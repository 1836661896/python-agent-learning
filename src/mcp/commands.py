import json
import shlex
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


def _coerce_value(text: str):
    t = text.strip()

    low = t.lower()
    if low == "true":
        return True

    if low == "false":
        return False

    if low in ("none", "null"):
        return None

    # int
    try:
        return int(t)
    except ValueError:
        pass

    # float
    try:
        return float(t)
    except ValueError:
        pass

    return t


def parse_kv_args(payload: str) -> dict[str, Any]:
    """
    解析 key=value 参数串。
    规则：
    - 参数以空格分隔，支持引号（由 shlex.split 处理）
    - 每个参数必须是 key=value
    - 重复 key 时报错（避免静默覆盖）
    """
    t = payload.strip()
    if not t:
        return {}

    try:
        parts = shlex.split(t)
    except ValueError:
        raise ValueError("参数引号格式错误：请检查单双引号是否成对出现")
    result: dict[str, Any] = {}
    for idx, part in enumerate(parts, 1):
        if "=" not in part:
            raise ValueError(f"第{idx}个参数格式错误：{part}（应为 key=value）")
        key, value = part.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise ValueError(f"第{idx}个参数名不能为空")
        if key in result:
            raise ValueError(f"参数重复：{key}（请只传一次）")
        result[key] = _coerce_value(value)
    return result


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

    return tool_name, parse_kv_args(payload)
