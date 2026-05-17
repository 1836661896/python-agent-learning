import json
import logging
import re
import textwrap
from typing import TypedDict

import anyio

from src.llm.completion import complete_chat
from src.llm.messages import build_user_message
from src.services.agent_presets import PRESET_SCHEDULE
from src.services.mcp_client import mcp_list_tools_async
from src.types import ArgsDict, MessageMode
from src.utils.json_coerce import extract_first_json_object

logger = logging.getLogger(__name__)

_SCHEDULE_KW = ("行程", "日程", "规划", "安排", "计划", "待办")


class AutoRouteResult(TypedDict):
    route: MessageMode
    mcp_tool: str | None
    mcp_arguments: ArgsDict
    preset: str | None


def _fallback_chat(*, preset: str | None = None) -> AutoRouteResult:
    """回退到普通对话"""
    return {"route": "chat", "mcp_tool": None, "mcp_arguments": {}, "preset": preset}


def _mcp_route(tool_name: str, arguments: ArgsDict | None = None) -> AutoRouteResult:
    args = arguments if isinstance(arguments, dict) else {}
    return {
        "route": "mcp",
        "mcp_tool": tool_name,
        "mcp_arguments": args,
        "preset": None,
    }


def _tool_schema_hint(tool: object) -> str:
    """从 MCP inputSchema 摘一行参数说明，供路由 prompt 使用。"""
    schema = getattr(tool, "inputSchema", None)
    if not isinstance(schema, dict):
        return ""
    props = schema.get("properties")
    if not isinstance(props, dict) or not props:
        return "参数：无或 mcp_arguments 用 {}"
    required = set(schema.get("required") or [])
    parts: list[str] = []
    for key, spec in props.items():
        if not isinstance(key, str):
            continue
        mark = "必填" if key in required else "可选"
        parts.append(f"{key}（{mark}）")
    return "参数：" + "、".join(parts[:6])


def _tool_has_required_args(tool: object) -> bool:
    """inputSchema 里是否存在 required 且非空。"""
    schema = getattr(tool, "inputSchema", None)
    if not isinstance(schema, dict):
        return False
    required = schema.get("required")
    return isinstance(required, list) and len(required) > 0


def _try_obvious_mcp_route(
    message: str, tools_by_name: dict[str, object]
) -> AutoRouteResult | None:
    """用户明确要调用某工具时，不经过 LLM 判别（工具名来自当次 tools/list）。"""
    text = message.strip()
    if not text or not tools_by_name:
        return None
    for name, tool in tools_by_name.items():
        pattern = rf"(调用|使用|执行|call)\s*{re.escape(name)}"
        if re.search(pattern, text, flags=re.IGNORECASE):
            if _tool_has_required_args(tool):
                return None
            return _mcp_route(name, {})
    return None


def _try_schedule_chat_route(message: str) -> AutoRouteResult | None:
    """行程类意图：走 chat + schedule preset，不调用 MCP 指南类工具。"""
    text = message.strip()
    if not text:
        return None
    if any(kw in text for kw in _SCHEDULE_KW):
        return _fallback_chat(preset=PRESET_SCHEDULE)
    return None


def decide_route_auto(message: str) -> AutoRouteResult:
    """routing=auto：tools/list → 规则兜底 → LLM 选 chat/mcp（参数由模型填）。"""
    try:
        list_result = anyio.run(mcp_list_tools_async)
        tools = list_result.tools or []
    except Exception:
        logger.exception("mcp_list_tools failed, fallback to chat")
        return _fallback_chat()

    lines: list[str] = []
    allowed: set[str] = set()
    tools_by_name: dict[str, object] = {}
    for t in tools:
        name = (getattr(t, "name", None) or "").strip()
        if not name:
            continue
        tools_by_name[name] = t
        allowed.add(name)
        desc = (getattr(t, "description", None) or "").strip()
        hint = _tool_schema_hint(t)
        line = f"- {name}: {desc or '(无描述)'}"
        if hint:
            line += f"；{hint}"
        lines.append(line)

    tools_block = "\n".join(lines) if lines else "(当前无工具，只能选 chat)"

    obvious = _try_obvious_mcp_route(message, tools_by_name)
    if obvious is not None:
        return obvious

    schedule_route = _try_schedule_chat_route(message)
    if schedule_route is not None:
        return schedule_route

    prompt = textwrap.dedent(f"""你是路由判别助手。只输出一个 JSON 对象，不要 Markdown、不要解释。

【可用工具】mcp 时 mcp_tool 必须是下列 name 之一：
{tools_block}

【用户消息】
{message.strip()}

【输出格式】
- route 为 "chat"：不要 mcp_tool、mcp_arguments（安排行程、日程规划也用 chat）
- route 为 "mcp"：必须有 mcp_tool（上表 name）、mcp_arguments（根据用户消息填写；无参则 {{}}）
- 禁止输出 route、mcp_tool、mcp_arguments 以外的键

【示例】
{{"route":"mcp","mcp_tool":"ping","mcp_arguments":{{}}}}
{{"route":"chat"}}
""").strip()

    try:
        raw = complete_chat(build_user_message(prompt))
        blob = extract_first_json_object(raw)
        data = json.loads(blob)
    except Exception:
        logger.exception("decide_route_auto parse failed")
        return _fallback_chat()

    route = data.get("route")
    if route == "chat":
        return _fallback_chat()
    if route != "mcp":
        return _fallback_chat()

    tool = data.get("mcp_tool")
    if not isinstance(tool, str) or not tool.strip():
        return _fallback_chat()
    name = tool.strip()
    if name not in allowed:
        logger.warning("auto picked unknown tool %s", name)
        return _fallback_chat()

    args = data.get("mcp_arguments")
    if not isinstance(args, dict):
        args = {}
    return _mcp_route(name, args)
