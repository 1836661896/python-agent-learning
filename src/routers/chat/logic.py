import logging
from collections.abc import Generator
from typing import Any

import httpx
from sqlalchemy.orm import Session

from src.api_response import fail, success
from src.llm.agent_plan import PlanError
from src.models.ConversationMessages import MessageRole
from src.routers.nl_utils import (
    ALLOWED_BUILTIN_CMDS,
    build_builtin_event_payload,
    build_mcp_event_payload,
    build_mcp_fail_data,
    is_allowed_nl_command,
    parse_manual_mcp_or_none,
)
from src.schemas import ChatRequest
from src.utils.obs_log import log_done, new_request_id

from .chat_turn import (
    FALLBACK_CHAT_META,
    _builtin_rejected_message,
    _prepare_planner_user_turn,
    _unwrap_plan_result,
)
from .deps import llm_client, mcp_client
from .events import (
    _record_builtin_rejected_event,
    _record_chat_event,
    _record_stream_chat_event,
    _record_stream_mcp_event,
    _stream_done_extra_for_mcp,
)
from .pkg import _chat_pkg
from .sse import (
    _mcp_sse_error,
    _over_chat,
    _sse_data,
    _stream_mcp_tool,
    _yield_sse_chat_stream,
)

logger = logging.getLogger(__name__)


def _make_request_done_logger(
    request_id: str,
    *,
    endpoint: str,
    done_event: str,
):
    def _done(
        route_kind: str,
        tool_succeeded: bool,
        plan_meta: dict[str, Any] | None = None,
        *,
        error: Exception | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        log_done(
            logger,
            event=done_event,
            endpoint=endpoint,
            request_id=request_id,
            route_kind=route_kind,
            tool_succeeded=tool_succeeded,
            plan_meta=plan_meta,
            error=error,
            extra=extra,
        )

    return _done


def _handle_builtin_non_stream(
    cmd: str,
    plan_meta: dict[str, Any],
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
    args: dict[str, Any],
    plan_meta: dict[str, Any] | None,
    done,
    request_id: str,
):
    """非流式 mcp 执行与响应组装。"""
    allowed = mcp_client.allowed_tool_names()
    if tool_name not in allowed:
        sorted_allowed = sorted(allowed)
        done(
            "mcp",
            False,
            plan_meta,
            extra={"error_type": "mcp_not_allowed", "error_msg": tool_name},
        )
        summary, payload = build_mcp_event_payload(
            route="mcp",
            tool_name=tool_name,
            plan_meta=plan_meta,
            tool_succeeded=False,
            error_type="mcp_not_allowed",
            allowed=sorted_allowed,
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
        return fail(
            "不允许调用该 MCP 工具",
            build_mcp_fail_data(
                tool_name=tool_name,
                allowed=sorted_allowed,
                planner_meta=plan_meta,
            ),
        )

    result = mcp_client.call_tool(tool_name, args)
    if not result.get("tool_succeeded"):
        detail = str(result)
        done(
            "mcp",
            False,
            plan_meta,
            extra={"error_type": "mcp_run_failed", "error_msg": detail},
        )
        summary, payload = build_mcp_event_payload(
            route="mcp",
            tool_name=tool_name,
            plan_meta=plan_meta,
            tool_succeeded=False,
            error_type="mcp_run_failed",
            detail=detail,
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
        return fail(
            "执行失败",
            build_mcp_fail_data(
                tool_name=tool_name,
                detail=detail,
                planner_meta=plan_meta,
            ),
        )

    done("mcp", True, plan_meta)
    result_data = result.get("data") or {}
    text = result_data.get("text", "")
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

    payload_resp = {"route": "mcp", "text": text, "result": result_data}
    if plan_meta is not None:
        payload_resp["planner_meta"] = plan_meta
    return success("MCP 工具调用成功", payload_resp)


def chat_endpoint(body: ChatRequest, db: Session):
    """非流式聊天：复用 planner 决策，返回文本 + planner_meta。"""
    request_id = new_request_id()
    _done = _make_request_done_logger(
        request_id,
        endpoint="/chat",
        done_event="chat_request_done",
    )

    try:
        # 1) 显式 mcp 调用
        parsed, mcp_err = parse_manual_mcp_or_none(body.message)
        if mcp_err is not None:
            _done(
                "mcp_parse_error",
                False,
                error=ValueError(mcp_err),
                extra={"error_type": "mcp_parse_error", "error_msg": mcp_err},
            )
            return fail("MCP 参数错误", {"route": "mcp", "detail": mcp_err})

        if parsed:
            tool_name, args = parsed
            manual_meta = {"provider_used": "manual_mcp", "fallback_used": False}
            return _handle_mcp_non_stream(
                tool_name, args, manual_meta, _done, request_id
            )

        # 2) 默认走 planner (会话 + 记忆包)
        try:
            conv, turn_id, augmented = _prepare_planner_user_turn(db, body, request_id)
        except ValueError:
            _done(
                "conversation_not_found",
                False,
                extra={"error_type": "conversation_not_found"},
            )
            return fail("会话不存在", {"route": "chat"})

        try:
            mcp_tools = mcp_client.list_tools()
            plan_result = llm_client.plan(
                user_text=augmented,
                mcp_tools=mcp_tools,
                allowed_builtin_cmds=ALLOWED_BUILTIN_CMDS,
            )
        except PlanError:
            reply = llm_client.chat_simple(augmented)
            _chat_pkg().append_message(
                db,
                conv.id,
                MessageRole.assistant,
                reply,
                turn_id,
                meta={
                    "request_id": request_id,
                    "route": "chat",
                    "planner_meta": FALLBACK_CHAT_META,
                },
            )
            db.commit()
            _chat_pkg().maybe_refine_memory(db, conv, llm_client)
            _done("chat", True, FALLBACK_CHAT_META)
            _record_chat_event(
                type_="chat",
                request_id=request_id,
                tool_succeeded=True,
                summary="planner fallback chat",
                payload={
                    "route": "chat",
                    "message": body.message,
                    "reply": reply,
                    "planner_meta": FALLBACK_CHAT_META,
                    "conversation_id": conv.id,
                    "turn_id": turn_id,
                },
                plan_meta=FALLBACK_CHAT_META,
                endpoint="/chat",
            )
            return success(
                "计划器 fallback 聊天回复成功",
                {
                    "route": "chat",
                    "text": reply,
                    "planner_meta": FALLBACK_CHAT_META,
                    "conversation_id": conv.id,
                },
            )

        plan, plan_meta = _unwrap_plan_result(plan_result)

        if plan["kind"] == "mcp":
            return _handle_mcp_non_stream(
                plan["tool_name"], plan["arguments"], plan_meta, _done, request_id
            )

        if plan["kind"] == "builtin":
            return _handle_builtin_non_stream(
                plan["command"], plan_meta, _done, request_id
            )

        # kind == chat
        reply = llm_client.chat_simple(augmented)
        _chat_pkg().append_message(
            db,
            conv.id,
            MessageRole.assistant,
            reply,
            turn_id,
            meta={
                "request_id": request_id,
                "route": "chat",
                "planner_meta": plan_meta,
            },
        )
        db.commit()
        _chat_pkg().maybe_refine_memory(db, conv, llm_client)
        _done("chat", True, plan_meta)
        _record_chat_event(
            type_="chat",
            request_id=request_id,
            tool_succeeded=True,
            summary="chat reply",
            payload={
                "route": "chat",
                "message": body.message,
                "reply": reply,
                "planner_meta": plan_meta,
                "conversation_id": conv.id,
                "turn_id": turn_id,
            },
            plan_meta=plan_meta,
            endpoint="/chat",
        )
        return success(
            "聊天回复成功",
            {
                "route": "chat",
                "text": reply,
                "planner_meta": plan_meta,
                "conversation_id": conv.id,
            },
        )

    except httpx.HTTPStatusError as e:
        _done("llm_http_error", False, error=e)
        db.rollback()
        return fail(f"LLM 返回异常：HTTP {e.response.status_code}")
    except httpx.RequestError as e:
        _done("llm_request_error", False, error=e)
        db.rollback()
        return fail("无法连接 LLM 服务，请检查配置与网络")
    except Exception as e:
        _done("runtime_error", False, error=e)
        db.rollback()
        return fail(str(e))


def event_stream(
    body: ChatRequest,
    request_id: str,
    db: Session,
) -> Generator[str, None, None]:
    """
    SSE: 根据意图走 mcp / builtin / chat 。
    在走 planner 前写入会话与用户消息：流式结束后写入助手消息并记事件。
    """
    message = body.message
    _s_done = _make_request_done_logger(
        request_id,
        endpoint="/chat/stream",
        done_event="chat_stream_done",
    )

    try:
        log_done(
            logger,
            event="chat_stream_start",
            endpoint="/chat/stream",
            request_id=request_id,
            route_kind="start",
            tool_succeeded=True,
        )

        parsed, mcp_err = parse_manual_mcp_or_none(message)
        if mcp_err is not None:
            _s_done(
                "mcp_parse_error",
                tool_succeeded=False,
                error=ValueError(mcp_err),
                extra={"error_type": "mcp_parse_error", "error_msg": mcp_err},
            )
            yield _mcp_sse_error("MCP 参数错误", detail=mcp_err)
            yield _over_chat()
            return

        if parsed:
            tool_name, args = parsed
            manual_meta = {"provider_used": "manual_mcp", "fallback_used": False}
            mcp_exec = yield from _stream_mcp_tool(tool_name, args, manual_meta)

            tool_succeeded = _record_stream_mcp_event(
                request_id, tool_name, manual_meta, mcp_exec
            )
            _s_done(
                "mcp",
                tool_succeeded,
                manual_meta,
                extra=None if tool_succeeded else _stream_done_extra_for_mcp(mcp_exec),
            )
            return

        # planner 前：会话 + 用户信息 + 记忆包
        try:
            conv, turn_id, augmented = _prepare_planner_user_turn(db, body, request_id)
        except ValueError:
            _s_done(
                "conversation_not_found",
                tool_succeeded=False,
                extra={"error_type": "conversation_not_found"},
            )
            yield _sse_data({"type": "error", "msg": "会话不存在", "route": "chat"})
            yield _over_chat()
            return

        try:
            mcp_tools = mcp_client.list_tools()
            plan_result = llm_client.plan(
                user_text=augmented,
                mcp_tools=mcp_tools,
                allowed_builtin_cmds=ALLOWED_BUILTIN_CMDS,
            )
        except PlanError:
            full_reply = yield from _yield_sse_chat_stream(augmented)
            _chat_pkg().append_message(
                db,
                conv.id,
                MessageRole.assistant,
                full_reply,
                turn_id,
                meta={
                    "request_id": request_id,
                    "route": "chat",
                    "planner_meta": FALLBACK_CHAT_META,
                },
            )
            db.commit()
            _chat_pkg().maybe_refine_memory(db, conv, llm_client)
            _s_done("chat", True, FALLBACK_CHAT_META)
            _record_stream_chat_event(
                request_id=request_id,
                message=message,
                plan_meta=FALLBACK_CHAT_META,
                summary="planner fallback chat",
                reply=full_reply,
                conversation_id=conv.id,
                turn_id=turn_id,
            )
            yield _over_chat()
            return

        plan, plan_meta = _unwrap_plan_result(plan_result)

        if plan["kind"] == "mcp":
            tool_name = plan["tool_name"]
            mcp_exec = yield from _stream_mcp_tool(
                tool_name, plan["arguments"], plan_meta
            )

            tool_succeeded = _record_stream_mcp_event(
                request_id, tool_name, plan_meta, mcp_exec
            )

            _s_done(
                "mcp",
                tool_succeeded,
                plan_meta,
                extra=None if tool_succeeded else _stream_done_extra_for_mcp(mcp_exec),
            )
            return

        if plan["kind"] == "builtin":
            cmd = plan["command"]

            if cmd == "unknown" or not is_allowed_nl_command(cmd):
                _s_done(
                    "builtin",
                    False,
                    plan_meta,
                    extra={
                        "error_type": "command_not_allowed",
                        "error_msg": f"command={cmd}",
                    },
                )
                _record_builtin_rejected_event(
                    request_id, cmd, plan_meta, endpoint="/chat/stream"
                )
                yield _sse_data(
                    {
                        "type": "delta",
                        "text": _builtin_rejected_message(cmd),
                    }
                )
                yield _over_chat()
                return

            tool_succeeded, tool_msg, data = _chat_pkg().run_tool(cmd)
            line = tool_msg
            if tool_succeeded:
                if data is not None and str(data).strip():
                    line = f"{tool_msg}\n{data}"
            else:
                line = f"执行失败：{tool_msg}"

            yield _sse_data({"type": "delta", "text": line})
            yield _sse_data(
                {
                    "type": "tool_result",
                    "tool_succeeded": bool(tool_succeeded),
                    "command": cmd,
                    "data": data,
                    "planner_meta": plan_meta,
                }
            )

            _s_done(
                "builtin",
                bool(tool_succeeded),
                plan_meta,
                extra=None
                if tool_succeeded
                else {"error_type": "builtin_run_failed", "error_msg": str(tool_msg)},
            )

            summary, payload = build_builtin_event_payload(
                cmd=cmd,
                plan_meta=plan_meta,
                tool_succeeded=bool(tool_succeeded),
                tool_msg=str(tool_msg),
                data=data,
            )
            _record_chat_event(
                type_="builtin",
                request_id=request_id,
                tool_succeeded=bool(tool_succeeded),
                summary=summary,
                payload=payload,
                plan_meta=plan_meta,
                endpoint="/chat/stream",
            )
            yield _over_chat()
            return

        full_reply2 = yield from _yield_sse_chat_stream(augmented)
        _chat_pkg().append_message(
            db,
            conv.id,
            MessageRole.assistant,
            full_reply2,
            turn_id,
            meta={"request_id": request_id, "route": "chat", "planner_meta": plan_meta},
        )
        db.commit()
        _chat_pkg().maybe_refine_memory(db, conv, llm_client)
        _s_done("chat", True, plan_meta)
        _record_stream_chat_event(
            request_id=request_id,
            message=message,
            plan_meta=plan_meta,
            summary="chat stream reply",
            reply=full_reply2,
            conversation_id=conv.id,
            turn_id=turn_id,
        )
        yield _over_chat()

    except httpx.HTTPStatusError as e:
        _s_done("llm_http_error", False, error=e)
        db.rollback()
        yield _sse_data(
            {"type": "error", "msg": f"LLM 返回异常： HTTP {e.response.status_code}"}
        )
        yield _over_chat()
    except httpx.RequestError as e:
        _s_done("llm_request_error", False, error=e)
        db.rollback()
        yield _sse_data({"type": "error", "msg": "无法连接 LLM，请检查配置与网络"})
        yield _over_chat()
    except Exception as e:
        _s_done("runtime_error", False, error=e)
        db.rollback()
        yield _sse_data({"type": "error", "msg": str(e)})
        yield _over_chat()
    finally:
        db.close()
