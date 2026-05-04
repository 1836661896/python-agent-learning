from typing import Final

from src.mcp.commands import parse_mcp_call

# 统一白名单：只开放低风险 builtin 命令给 NL planner。
ALLOWED_BUILTIN_CMDS: Final[set[str]] = {"list", "time", "help", "version", "echo", "add"}


def is_allowed_nl_command(cmd: str) -> bool:
    """校验 NL 规划出的 builtin 命令是否在允许范围内。"""
    if cmd in ("list", "time", "help", "version"):
        return True
    return cmd.startswith("echo ") or cmd.startswith("add ")


def is_explicit_mcp_text(text: str) -> bool:
    """判断是否是用户显式 MCP 调用语法。"""
    lowered = text.strip().lower()
    return lowered.startswith("mcp ") or lowered.startswith("调用mcp ")


def parse_manual_mcp_or_none(message: str) -> tuple[tuple[str, dict] | None, str | None]:
    """
    尝试解析显式 MCP 调用：
    - 返回 (parsed, None)：解析成功或非 MCP 文本（parsed 可能是 None）
    - 返回 (None, error_detail)：是 MCP 文本但参数错误
    """
    try:
        parsed = parse_mcp_call(message)
    except ValueError as exc:
        if is_explicit_mcp_text(message):
            return None, str(exc)
        raise
    return parsed, None


def build_mcp_event_payload(
    *,
    route: str,
    tool_name: str,
    plan_meta: dict | None,
    ok_flag: bool,
    result_data: dict | None = None,
    error_type: str | None = None,
    detail: str | None = None,
    allowed: list[str] | None = None,
) -> tuple[str, dict]:
    """统一组装 MCP 事件 payload，避免在多个路由重复拼装。"""
    payload: dict = {
        "route": route,
        "tool_name": tool_name,
        "planner_meta": plan_meta,
    }
    if ok_flag:
        payload["result"] = result_data or {}
        return f"mcp success: {tool_name}", payload

    payload["error_type"] = error_type or "mcp_run_failed"
    if detail is not None:
        payload["detail"] = detail
    if allowed is not None:
        payload["allowed"] = allowed
    return "mcp failed", payload


def build_mcp_fail_data(
    *,
    route: str = "mcp",
    tool_name: str = "",
    detail: str = "",
    allowed: list[str] | None = None,
    planner_meta: dict | None = None,
) -> dict:
    """统一组装 MCP 失败响应 data。"""
    data: dict = {"route": route}
    if tool_name:
        data["tool_name"] = tool_name
    if detail:
        data["detail"] = detail
    if allowed is not None:
        data["allowed"] = allowed
    if planner_meta is not None:
        data["planner_meta"] = planner_meta
    return data


def build_builtin_event_payload(
    *,
    cmd: str,
    plan_meta: dict | None,
    ok_flag: bool,
    tool_msg: str,
    data,
) -> tuple[str, dict]:
    """统一组装 builtin 事件 payload，避免多个路由重复拼装。"""
    payload: dict = {
        "route": "builtin",
        "command": cmd,
        "tool_msg": tool_msg,
        "planner_meta": plan_meta,
    }
    if ok_flag:
        payload["result"] = data
        return f"builtin success: {cmd}", payload

    payload["error_type"] = "builtin_run_failed"
    return f"builtin failed: {cmd}", payload
