from src.api_response import fail, success
from src.routers.nl_utils import (
    build_builtin_event_payload,
    is_allowed_nl_command,
)

from .chat_turn import _builtin_rejected_message
from .deps import mcp_client
from .events import _record_builtin_rejected_event, _record_chat_event
from .mcp_outcomes import (
    finalize_mcp_non_stream_failure,
    finalize_mcp_non_stream_success,
)
from .pkg import _chat_pkg
from .types import ArgsDict


def _handle_builtin_non_stream(
    cmd: str,
    plan_meta: ArgsDict,
    done,
    request_id: str,
):
    """非流式 builtin 执行与响应组装。"""
    if cmd == "unknown" or not is_allowed_nl_command(cmd):
        done(
            "builtin",
            False,
            plan_meta,
            extra={"error_type": "command_not_allowed", "error_msg": f"command={cmd}"},
        )
        _record_builtin_rejected_event(request_id, cmd, plan_meta, endpoint="/chat")
        return fail(
            _builtin_rejected_message(cmd),
            {"route": "builtin", "command": cmd, "planner_meta": plan_meta},
        )

    tool_succeeded, tool_msg, data = _chat_pkg().run_tool(cmd)
    summary, payload = build_builtin_event_payload(
        cmd=cmd,
        plan_meta=plan_meta,
        tool_succeeded=tool_succeeded,
        tool_msg=str(tool_msg),
        data=data,
    )

    if tool_succeeded:
        done("builtin", True, plan_meta)
        text = tool_msg if not data else f"{tool_msg}\n{data}"
        _record_chat_event(
            type_="builtin",
            request_id=request_id,
            tool_succeeded=True,
            summary=summary,
            payload=payload,
            plan_meta=plan_meta,
            endpoint="/chat",
        )
        return success(
            "builtin 执行成功",
            {
                "route": "builtin",
                "command": cmd,
                "text": text,
                "result": data,
                "planner_meta": plan_meta,
            },
        )

    done(
        "builtin",
        False,
        plan_meta,
        extra={"error_type": "builtin_run_failed", "error_msg": str(tool_msg)},
    )
    _record_chat_event(
        type_="builtin",
        request_id=request_id,
        tool_succeeded=False,
        summary=summary,
        payload=payload,
        plan_meta=plan_meta,
        endpoint="/chat",
    )
    return fail(
        "执行失败",
        {
            "route": "builtin",
            "command": cmd,
            "tool_msg": tool_msg,
            "planner_meta": plan_meta,
        },
    )


def _handle_mcp_non_stream(
    tool_name: str,
    args: ArgsDict,
    plan_meta: ArgsDict | None,
    done,
    request_id: str,
):
    """非流式 MCP：执行与响应组装。"""
    allowed = mcp_client.allowed_tool_names()
    if tool_name not in allowed:
        return finalize_mcp_non_stream_failure(
            done=done,
            request_id=request_id,
            tool_name=tool_name,
            plan_meta=plan_meta,
            error_type="mcp_not_allowed",
            fail_msg="不允许调用该 MCP 工具",
            sorted_allowed=sorted(allowed),
        )

    result = mcp_client.call_tool(tool_name, args)
    if not result.get("tool_succeeded"):
        detail = str(result)
        return finalize_mcp_non_stream_failure(
            done=done,
            request_id=request_id,
            tool_name=tool_name,
            plan_meta=plan_meta,
            error_type="mcp_run_failed",
            fail_msg="执行失败",
            detail=detail,
        )

    result_data = result.get("data") or {}
    text = result_data.get("text", "")
    return finalize_mcp_non_stream_success(
        done=done,
        request_id=request_id,
        tool_name=tool_name,
        plan_meta=plan_meta,
        result_data=result_data,
        text=text,
    )
