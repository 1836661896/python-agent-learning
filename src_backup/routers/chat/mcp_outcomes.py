"""MCP 结果收口：非流式记事件 + HTTP 返回；SSE 在 yield 结束后记事件 + log_done。"""

from collections.abc import Callable
from typing import Any

from src.api_response import fail, success
from src.routers.nl_utils import build_mcp_event_payload, build_mcp_fail_data

from .events import (
    _record_chat_event,
    _record_stream_mcp_event,
    _stream_done_extra_for_mcp,
)
from .types import ArgsDict


def finalize_mcp_non_stream_failure(
    *,
    done: Callable[..., None],
    request_id: str,
    tool_name: str,
    plan_meta: ArgsDict | None,
    error_type: str,
    fail_msg: str,
    sorted_allowed: list[str] | None = None,
    detail: str = "",
) -> Any:
    """非流式 MCP 失败：done → build_mcp_event_payload → 记事件 → fail。"""
    if error_type == "mcp_not_allowed":
        done_extra: ArgsDict = {
            "error_type": "mcp_not_allowed",
            "error_msg": tool_name,
        }
    else:
        done_extra = {"error_type": "mcp_run_failed", "error_msg": detail}
    done("mcp", False, plan_meta, extra=done_extra)

    summary, payload = build_mcp_event_payload(
        route="mcp",
        tool_name=tool_name,
        plan_meta=plan_meta,
        tool_succeeded=False,
        error_type=error_type,
        allowed=sorted_allowed,
        detail=detail if detail else None,
    )
    _record_chat_event(
        type_="mcp",
        request_id=request_id,
        tool_succeeded=False,
        summary=summary,
        payload=payload,
        plan_meta=plan_meta,
        endpoint="/chat",
    )
    if error_type == "mcp_not_allowed":
        fd = build_mcp_fail_data(
            tool_name=tool_name, allowed=sorted_allowed, planner_meta=plan_meta
        )
    else:
        fd = build_mcp_fail_data(
            tool_name=tool_name, detail=detail, planner_meta=plan_meta
        )
    return fail(fail_msg, fd)


def finalize_mcp_non_stream_success(
    *,
    done: Callable[..., None],
    request_id: str,
    tool_name: str,
    plan_meta: ArgsDict | None,
    result_data: ArgsDict,
    text: str,
) -> Any:
    """非流式 MCP 成功：done → build_mcp_event_payload → 记事件 → success。"""
    done("mcp", True, plan_meta)
    summary, payload_event = build_mcp_event_payload(
        route="mcp",
        tool_name=tool_name,
        plan_meta=plan_meta,
        tool_succeeded=True,
        result_data=result_data,
    )
    _record_chat_event(
        type_="mcp",
        request_id=request_id,
        tool_succeeded=True,
        summary=summary,
        payload=payload_event,
        plan_meta=plan_meta,
        endpoint="/chat",
    )
    payload_resp: ArgsDict = {"route": "mcp", "text": text, "result": result_data}
    if plan_meta is not None:
        payload_resp["planner_meta"] = plan_meta
    return success("MCP 工具调用成功", payload_resp)


def finalize_stream_mcp_turn(
    request_id: str,
    tool_name: str,
    plan_meta: ArgsDict | None,
    mcp_exec: ArgsDict,
    s_done: Callable[..., None],
) -> bool:
    """
    SSE：在 yield from _stream_mcp_tool 之后调用。
    成功 / 失败共用（由 mcp_exec['tool_succeeded'] 区分），记流式事件并打 _s_done。
    """
    tool_succeeded = _record_stream_mcp_event(
        request_id, tool_name, plan_meta, mcp_exec
    )
    s_done(
        "mcp",
        tool_succeeded,
        plan_meta,
        extra=None if tool_succeeded else _stream_done_extra_for_mcp(mcp_exec),
    )
    return tool_succeeded
