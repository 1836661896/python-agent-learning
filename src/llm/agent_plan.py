import json
import logging
import os
from typing import Any

import httpx

DEFAULT_BASE = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen2.5:3b"
TIMEOUT_SEC = 120.0

logger = logging.getLogger(__name__)


def plan_with_llm(
    user_text: str,
    mcp_tools: list[dict[str, Any]],
    allowed_builtin_cmds: set[str],
) -> dict[str, Any]:
    provider = os.getenv("LLM_PROVIDER", "ollama").strip().lower()
    fallback = os.getenv("LLM_FALLBACK_PROVIDER", "").strip().lower()

    def _run(p: str) -> dict[str, Any]:
        if p == "ollama":
            return plan_with_ollama(user_text, mcp_tools, allowed_builtin_cmds)
        if p == "zhipu":
            return plan_with_zhipu(user_text, mcp_tools, allowed_builtin_cmds)
        raise PlanError(f"不支持的 LLM_PROVIDER： {p}")

    try:
        plan = _run(provider)
        return {
            "plan": plan,
            "meta": {"provider_used": provider, "fallback_used": False},
        }
    except PlanError as first_err:
        # 没配置 fallback，或 fallback 和主 provider 相同 -> 直接抛出
        if not fallback or fallback == provider:
            raise first_err

        logger.warning(
            "planner primary provider failed, trying fallback: primary=%s fallback=%s err=%s",
            provider,
            fallback,
            str(first_err),
        )

        try:
            out = _run(fallback)
            logger.warning(
                "planner fallback succeeded: primary=%s fallback=%s", provider, fallback
            )
            return {
                "plan": out,
                "meta": {"provider_used": fallback, "fallback_used": True},
            }
        except PlanError as second_err:
            logger.error(
                "planner fallback failed: primary=%s fallback=%s primary_err=%s fallback_err=%s",
                provider,
                fallback,
                str(first_err),
                str(second_err),
            )
            raise PlanError(
                f"主 provider（{provider}）失败：{first_err};"
                f"fallback（{fallback}）也失败：{second_err}"
            )


def plan_with_zhipu(
    user_text: str,
    mcp_tools: list[dict[str, Any]],
    allowed_builtin_cmds: set[str],
) -> dict[str, Any]:
    """
    用智谱生成 plan JSON，再用 validate_plan 做强校验。
    """
    allowed_mcp_tools = {t["name"] for t in mcp_tools if isinstance(t.get("name"), str)}

    tools_text = _build_tools_text(mcp_tools)
    builtin_text = ", ".join(sorted(allowed_builtin_cmds))

    system_prompt = (
        "你是任务规划器。"
        "你只能输出一行 JSON， 不要解释，不要 MarkDown， 不要代码块。"
        "JSON 必须是以下三种之一："
        '{"kind": "mcp", "tool_name": "<name>", "arguments": {...}} 或'
        '{"kind": "builtin", "command": "<cmd>"} 或 '
        '{"kind": "chat", "answer_hint": ""}。'
        f"内置命令仅允许：{builtin_text}。"
        "MCP 工具仅允许从我提过的工具列表里选择。"
        f"MCP 工具列表如下： {tools_text}"
    )

    api_key = os.getenv("ZHIPU_API_KEY", "").strip()
    if not api_key:
        raise ValueError("缺少 ZHIPU_API_KEY，请先在 .env 中配置")

    base_url = os.getenv(
        "ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"
    ).rstrip("/")
    model = os.getenv("ZHIPU_MODEL", "glm-4-flash")
    url = f"{base_url}/chat/completions"

    header = {
        "Anthorzation": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [
            {"roles": "system", "content": system_prompt},
            {"roles": "user", "content": user_text},
        ],
        "stream": False,
    }

    try:
        with httpx.Client(timeout=TIMEOUT_SEC, trust_env=False) as client:
            resp = client.post(url, headers=header, json=payload)
            resp.raise_for_status()
            data = resp.json()

    except httpx.HTTPStatusError as e:
        raise PlanError(f"智谱 HTTP 异常： {e.response.status_code}")

    except httpx.RequestError:
        raise PlanError("无法连接智谱服务，请检查网络或 BASE_URL")

    try:
        content = data["choices"][0]["message"]["content"]
    except Exception:
        raise PlanError("智谱返回为空，无法生成 plan")

    if not isinstance(content, str) or not content.strip():
        raise PlanError("智谱返回为空，无法生成 plan")

    plan = parse_plan_json(content)
    return validate_plan(plan, allowed_mcp_tools, allowed_builtin_cmds)


def _build_tools_text(mcp_tools: list[dict[str, Any]]) -> str:
    """
    把 MCP 工具列表压缩成给模型看的文本（只保留关键字段）。
    """
    slim_tools = []
    for t in mcp_tools:
        name = t.get("name", "")
        desc = t.get("description", "")
        schema = t.get("input_schema", {})
        if isinstance(name, str) and name.strip():
            slim_tools.append(
                {
                    "name": name,
                    "description": desc if isinstance(desc, str) else "",
                    "input_schema": schema if isinstance(schema, dict) else {},
                }
            )
    return json.dumps(slim_tools, ensure_ascii=False)


def plan_with_ollama(
    user_text: str,
    mcp_tools: list[dict[str, Any]],
    allowed_builtin_cmds: set[str],
) -> dict[str, Any]:
    """
    用 Ollama 生成 plan JSON，再用 validate_plan 做强校验。
    """
    allowed_mcp_tools = {t["name"] for t in mcp_tools if isinstance(t.get("name"), str)}

    tools_text = _build_tools_text(mcp_tools)
    builtin_text = ", ".join(sorted(allowed_builtin_cmds))

    system_prompt = (
        "你是任务规划器。"
        "你只能输出一行 JSON，不要解释，不要Markdown， 不要代码块。"
        "JSON 必须是以下三种之一："
        '{"kind":"mcp","tool_name":"<name>","arguments":{...}} 或 '
        '{"kind":"builtin","command":"<cmd>"} 或 '
        '{"kind":"chat","answer_hint":""}。'
        f"内置命令仅允许：{builtin_text}。"
        "MCP 工具仅允许从我提供的工具列表里选择。"
        f"MCP 工具列表如下：{tools_text}"
    )

    base = os.getenv("OLLAMA_BASE_URL", DEFAULT_BASE).rstrip("/")
    model = os.getenv("OLLAMA_MODEL", DEFAULT_MODEL)
    url = f"{base}/api/chat"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        "stream": False,
    }

    try:
        with httpx.Client(timeout=TIMEOUT_SEC, trust_env=False) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        raise PlanError(f"Ollama HTTP 异常：{e.response.status_code}")
    except httpx.RequestError:
        raise PlanError("无法连接 Ollama，请确认服务已启动")

    content = (data.get("message") or {}).get("content")
    if not isinstance(content, str) or not content.strip():
        raise PlanError("Ollama 返回为空，无法生成 plan")

    plan = parse_plan_json(content)
    return validate_plan(plan, allowed_mcp_tools, allowed_builtin_cmds)


class PlanError(ValueError):
    """规划结果不合法时抛出。"""


def extract_json_text(raw: str) -> str:
    """
    兼容模型偶发输出：
    - 纯JSON
    - ```json ...``` 代码块
    """
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.startswith("json"):
            text = text[len("json") :].strip()
    return text


def parse_plan_json(raw: str) -> dict[str, Any]:
    text = extract_json_text(raw).strip()
    decoder = json.JSONDecoder()

    # 1) 优先整段解析
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj

    except Exception:
        pass

    # 2) 允许模型前后带点杂质： 从第一个 { 开始解析首个对象
    start = text.find("{")
    if start != -1:
        try:
            obj, _ = decoder.raw_decode(text[start:])
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

    raise PlanError("模型输出不是合法 JSON 对象")


def validate_plan(
    plan: dict[str, Any],
    allowed_mcp_tools: set[str],
    allowed_builtin_cmds: set[str],
) -> dict[str, Any]:
    kind = plan.get("kind")
    if kind not in {"mcp", "builtin", "chat"}:
        raise PlanError("kind 必须是 mcp / builtin / chat")

    if kind == "mcp":
        tool_name = plan.get("tool_name")
        arguments = plan.get("arguments", {})
        if not isinstance(tool_name, str) or not tool_name.strip():
            raise PlanError("mcp 计划缺少 tool_name")
        if tool_name not in allowed_mcp_tools:
            raise PlanError(f"不允许的 MCP 工具： {tool_name}")
        if not isinstance(arguments, dict):
            raise PlanError("mcp.arguments 必须是对象")
        return {"kind": "mcp", "tool_name": tool_name, "arguments": arguments}

    if kind == "builtin":
        command = plan.get("command")
        if not isinstance(command, str) or not command.strip():
            raise PlanError("builtin 计划缺少 command")
        # 先只校验首词，后续可换为更严格白名单
        cmd_head = command.strip().split(" ", 1)[0].lower()
        if cmd_head not in allowed_builtin_cmds:
            raise PlanError(f"不允许的内置命令： {command}")
        return {"kind": "builtin", "command": command.strip()}

    # chat
    answer_hint = plan.get("answer_hint", "")
    if not isinstance(answer_hint, str):
        answer_hint = ""
    return {"kind": "chat", "answer_hint": answer_hint.strip()}
