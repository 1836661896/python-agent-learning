import json
import logging
import textwrap
from typing import TypedDict

import anyio

from src.llm.completion import complete_ollama_chat
from src.llm.messages import build_user_message
from src.services.mcp_client import mcp_list_tools_async
from src.types import ArgsDict, MessageMode

logger = logging.getLogger(__name__)


class AutoRouteResult(TypedDict):
    route: MessageMode
    mcp_tool: str | None
    mcp_arguments: ArgsDict


def _coerce_route_json_text(raw: str) -> str:
    """与 conversation_refine 类似：去掉围栏，截取第一个 { ... }。"""
    text = (raw or "").strip()
    if not text:
        raise ValueError("返回数据为空")
    if text.startswith("```"):
        lines = text.splitlines()
        if lines:
            lines = lines[1:]
        while lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    if text.startswith("{"):
        return text
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("未找到 JSON 对象")
    return text[start : end + 1]


def _fallback_chat() -> AutoRouteResult:
    return {"route": "chat", "mcp_tool": None, "mcp_arguments": {}}


def decide_route_auto(message: str) -> AutoRouteResult:
    """routing=auto 时：拉工具列表 -> 问大模型 -> 解析 JSON。"""
    try:
        list_result = anyio.run(mcp_list_tools_async)
        tools = list_result.tools or []
    except Exception:
        logger.exception("mcp_list_tools failed, fallback to chat")
        return _fallback_chat()

    lines: list[str] = []
    allowed: set[str] = set()
    for t in tools:
        name = (getattr(t, "name", None) or "").strip()
        if not name:
            continue
        allowed.add(name)
        desc = (getattr(t, "description", None) or "").strip()
        lines.append(f"- {name}: {desc or '(无描述)'}")

    tools_block = "\n".join(lines) if lines else "(当前无工具，只能选 chat)"

    prompt = textwrap.dedent(f"""你是路由判别助手。根据【用户消息】决定本轮走普通对话(chat)还是调用工具(mcp)。
【可用工具】（mcp 时 mcp_tool 必须是下列 name 之一）：
{tools_block}
【用户消息】
{message.strip()}
只输出一个 JSON 对象，不要其它文字、不要 Markdown 围栏：
- "route": "chat" 或 "mcp"（不要输出 plan）
- route 为 "mcp" 时必须有 "mcp_tool": 字符串, "mcp_arguments": 对象（无参则 {{}})
- route 为 "chat" 时不要 mcp_tool / mcp_arguments
""").strip()

    try:
        raw = complete_ollama_chat(build_user_message(prompt))
        data = json.loads(_coerce_route_json_text(raw))
    except Exception:
        logger.exception("decide_route_auto parse failed")
        return _fallback_chat()

    route = data.get("route")
    if route == "chat":
        return {"route": "chat", "mcp_tool": None, "mcp_arguments": {}}
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
    return {"route": "mcp", "mcp_tool": name, "mcp_arguments": args}
