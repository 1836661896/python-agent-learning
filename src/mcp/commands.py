import json
from typing import Any


def match_mcp_tool(text: str) -> str | None:
    t = text.strip().lower()
    if not t:
        return None

    # 兼容中文口令：调用 mcp ping
    if t.startswith("调用mcp "):
        tool = t.removeprefix("调用mcp ").strip()
        return tool or None

    # 通用形式： mcp ping
    if t.startswith("mcp "):
        tool = t.removeprefix("mcp ").strip()
        return tool or None

    return None


def parse_mcp_call(text: str) -> tuple[str, dict[str, Any]] | None:
    """
    支持：
    - mcp <tool>
    - mcp <tool> <json>
    - 调用mcp <tool>
    - 调用mcp <tool> <json>
    """
    t = text.strip()
    if not t:
        return None

    low = t.lower()
    if low.startswith("调用mcp "):
        rest = t[len("调用mcp ") :].strip()
    elif low.startswith("mcp "):
        rest = t[len("mcp ") :].strip()
    else:
        return None

    if not rest:
        return None

    # 取第一个 token 作为 tool_name，剩下的作为payload
    parts = rest.split(" ", 1)
    tool_name = parts[0].strip()
    payload = parts[1].strip() if len(parts) == 2 else ""

    if not payload:
        return tool_name, {}

    # 如果 payload 以 { 开头，按 JSON 解析
    if payload.startswith("{"):
        obj = json.loads(payload)
        if not isinstance(obj, dict):
            raise ValueError("MCP args 必须是 JSON 对象（dict）")
        return tool_name, obj

    raise ValueError("参数格式不支持：请使用 JSON，例如 mcp ping {}")
