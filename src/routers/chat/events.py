from src.routers.nl_utils import build_mcp_event_payload

from .pkg import _chat_pkg
from .types import ArgsDict


def _record_chat_event(
    type_: str,
    request_id: str,
    tool_succeeded: bool,
    summary: str,
    payload: ArgsDict,
    plan_meta: ArgsDict | None = None,
    endpoint: str = "/chat",
) -> None:
    """统一记录聊天事件，支持区分非流式和流式端点。"""
    meta = plan_meta or {}
    _chat_pkg().record_event(
        type_=type_,
        endpoint=endpoint,
        request_id=request_id,
        tool_succeeded=tool_succeeded,
        provider_used=meta.get("provider_used", "unknown"),
        fallback_used=bool(meta.get("fallback_used", False)),
        summary=summary,
        payload=payload,
    )


def _record_builtin_rejected_event(
    request_id: str,
    cmd: str,
    plan_meta: ArgsDict | None,
    endpoint: str,
) -> None:
    """统一记录 builtin 命令被拒绝事件。"""
    _record_chat_event(
        type_="builtin",
        request_id=request_id,
        tool_succeeded=False,
        summary="builtin rejected",
        payload={
            "route": "builtin",
            "command": cmd,
            "error_type": "command_not_allowed",
            "planner_meta": plan_meta,
        },
        plan_meta=plan_meta,
        endpoint=endpoint,
    )


def _stream_done_extra_for_mcp(mcp_exec: ArgsDict) -> dict[str, str]:
    """统一 mcp 失败日志字段，避免手动/plan 两条路径重复拼装。"""
    return {
        "error_type": mcp_exec.get("error_type", "mcp_run_failed"),
        "error_msg": str(
            mcp_exec.get("detail") or mcp_exec.get("allowed") or "mcp failed"
        ),
    }


def _record_stream_mcp_event(
    request_id: str,
    tool_name: str,
    plan_meta: ArgsDict | None,
    mcp_exec: ArgsDict,
) -> bool:
    """
    统一记录流式 mcp 事件，并返回 tool_succeeded。
    - 手动 mcp 和 planner->mcp 共用
    - 保证 summary/payload 结构一致
    """
    tool_succeeded = bool(mcp_exec.get("tool_succeeded"))
    summary, payload = build_mcp_event_payload(
        route="mcp",
        tool_name=tool_name,
        plan_meta=plan_meta,
        tool_succeeded=tool_succeeded,
        result_data=mcp_exec.get("result"),
        error_type=mcp_exec.get("error_type"),
        detail=mcp_exec.get("detail"),
        allowed=mcp_exec.get("allowed"),
    )
    _record_chat_event(
        type_="mcp",
        request_id=request_id,
        tool_succeeded=tool_succeeded,
        summary=summary,
        payload=payload,
        plan_meta=plan_meta,
        endpoint="/chat/stream",
    )
    return tool_succeeded


def _record_stream_chat_event(
    request_id: str,
    message: str,
    plan_meta: ArgsDict | None,
    summary: str,
    *,
    reply: str = "",
    conversation_id: int | None = None,
    turn_id: str | None = None,
) -> None:
    """流式 chat 事件：payload 带完整 reply 与 conversation 信息。"""
    payload: ArgsDict = {
        "route": "chat",
        "message": message,
        "reply": reply,
        "planner_meta": plan_meta,
    }
    if conversation_id is not None:
        payload["conversation_id"] = conversation_id
    if turn_id is not None:
        payload["turn_id"] = turn_id
    _record_chat_event(
        type_="chat",
        request_id=request_id,
        tool_succeeded=True,
        summary=summary,
        payload=payload,
        endpoint="/chat/stream",
        plan_meta=plan_meta,
    )
