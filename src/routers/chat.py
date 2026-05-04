import json
import logging
from collections.abc import Generator
from typing import Any

import httpx
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.agent_service import run_tool
from src.api_response import fail, ok
from src.llm import get_llm_client
from src.llm.agent_plan import PlanError
from src.mcp import MCPClient
from src.routers.nl_utils import (
    ALLOWED_BUILTIN_CMDS,
    build_builtin_event_payload,
    build_mcp_event_payload,
    is_allowed_nl_command,
    parse_manual_mcp_or_none,
)
from src.schemas import ChatRequest
from src.services.event_services import record_event
from src.utils.obs_log import log_done, new_request_id

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])
mcp_client = MCPClient()
llm_client = get_llm_client()

FALLBACK_CHAT_META = {"provider_used": "planner_fallback_chat", "fallback_used": True}


def _record_chat_event(
    type_: str,
    request_id: str,
    ok_flag: bool,
    summary: str,
    payload: dict[str, Any],
    plan_meta: dict[str, Any] | None = None,
    endpoint: str = "/chat",
) -> None:
    """统一记录聊天事件，支持区分非流式与流式端点。"""
    meta = plan_meta or {}
    record_event(
        type_=type_,
        endpoint=endpoint,
        request_id=request_id,
        ok=ok_flag,
        provider_used=meta.get("provider_used", "unknown"),
        fallback_used=bool(meta.get("fallback_used", False)),
        summary=summary,
        payload=payload,
    )


def _sse_data(obj: dict[str, Any]) -> str:
    """单条 SSE：data 后为 JSON，结尾空行。"""
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


def _over_chat() -> str:
    """统一结束事件。"""
    return _sse_data({"type": "done"})


def _unwrap_plan_result(plan_result: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """统一拆包 planner 返回：{'plan': ..., 'meta': ...}。"""
    plan = plan_result["plan"]
    plan_meta = plan_result.get("meta", {})
    return plan, plan_meta


def _record_builtin_rejected_event(
    request_id: str,
    cmd: str,
    plan_meta: dict[str, Any] | None,
    endpoint: str,
) -> None:
    """统一记录 builtin 命令被拒绝事件。"""
    _record_chat_event(
        type_="builtin",
        request_id=request_id,
        ok_flag=False,
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


def _builtin_rejected_message(cmd: str) -> str:
    """统一被拒绝提示文案，避免非流式/流式写两份。"""
    return (
        "当前无法把这句话安全的转成可执行命令，或不在允许范围内。"
        f"（解析结果：{cmd}；允许： list/time/help/version/echo.../add...）"
    )


def _mcp_sse_error(
    msg: str,
    detail: str = "",
    tool_name: str = "",
    allowed: list[str] | None = None,
) -> str:
    payload: dict[str, Any] = {"type": "error", "msg": msg, "route": "mcp"}
    if detail:
        payload["detail"] = detail
    if tool_name:
        payload["tool_name"] = tool_name
    if allowed is not None:
        payload["allowed"] = allowed
    return _sse_data(payload)


def _stream_mcp_tool(
    tool_name: str,
    args: dict[str, Any],
    plan_meta: dict[str, Any] | None = None,
) -> Generator[str, None, dict[str, Any]]:
    """
    流式执行 MCP 工具：
    - 产出 SSE 文本
    - return 执行摘要（ok/error/result），供外层统一写日志与事件
    """
    allowed = mcp_client.allowed_tool_names()
    if tool_name not in allowed:
        sorted_allowed = sorted(allowed)
        yield _mcp_sse_error(
            "不允许调用该 MCP 工具",
            tool_name=tool_name,
            allowed=sorted_allowed,
        )
        yield _over_chat()
        return {
            "ok": False,
            "tool_name": tool_name,
            "error_type": "mcp_not_allowed",
            "allowed": sorted_allowed,
        }

    result = mcp_client.call_tool(tool_name, args)
    if not result.get("ok"):
        detail = str(result)
        yield _mcp_sse_error(
            result.get("msg", "tool error"),
            tool_name=tool_name,
            detail=detail,
        )
        yield _over_chat()
        return {
            "ok": False,
            "tool_name": tool_name,
            "error_type": "mcp_run_failed",
            "detail": detail,
        }

    data = result.get("data") or {}
    yield _sse_data({"type": "delta", "text": data.get("text", "")})
    yield _sse_data(
        {
            "type": "tool_result",
            "ok": True,
            "route": "mcp",
            "tool_name": tool_name,
            "data": data,
            "planner_meta": plan_meta or {},
        }
    )
    yield _over_chat()
    return {"ok": True, "tool_name": tool_name, "result": data}


def _stream_done_extra_for_mcp(mcp_exec: dict[str, Any]) -> dict[str, str]:
    """统一 mcp 失败日志字段，避免手动/plan 两条路径重复拼装。"""
    return {
        "error_type": mcp_exec.get("error_type", "mcp_run_failed"),
        "error_msg": str(mcp_exec.get("detail") or mcp_exec.get("allowed") or "mcp failed"),
    }


def _record_stream_mcp_event(
    request_id: str,
    tool_name: str,
    plan_meta: dict[str, Any] | None,
    mcp_exec: dict[str, Any],
) -> bool:
    """
    统一记录流式 mcp 事件，并返回 ok_flag。
    - 手动 mcp 和 planner->mcp 共用
    - 保证 summary/payload 结构一致
    """
    ok_flag = bool(mcp_exec.get("ok"))
    summary, payload = build_mcp_event_payload(
        route="mcp",
        tool_name=tool_name,
        plan_meta=plan_meta,
        ok_flag=ok_flag,
        result_data=mcp_exec.get("result"),
        error_type=mcp_exec.get("error_type"),
        detail=mcp_exec.get("detail"),
        allowed=mcp_exec.get("allowed"),
    )
    _record_chat_event(
        type_="mcp",
        request_id=request_id,
        ok_flag=ok_flag,
        summary=summary,
        payload=payload,
        plan_meta=plan_meta,
        endpoint="/chat/stream",
    )
    return ok_flag


def _record_stream_chat_event(
    request_id: str,
    message: str,
    plan_meta: dict[str, Any] | None,
    summary: str,
) -> None:
    """流式 chat 事件统一入口：不在这里聚合完整 reply，避免引入额外状态复杂度。"""
    _record_chat_event(
        type_="chat",
        request_id=request_id,
        ok_flag=True,
        summary=summary,
        payload={
            "route": "chat",
            "message": message,
            "reply": "",
            "planner_meta": plan_meta,
        },
        plan_meta=plan_meta,
        endpoint="/chat/stream",
    )


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
            "当前无法把这句话安全转成可执行命令，或不在允许范围内",
            {"route": "builtin", "command": cmd, "planner_meta": plan_meta},
        )

    ok_flag, tool_msg, data = run_tool(cmd)
    summary, payload = build_builtin_event_payload(
        cmd=cmd,
        plan_meta=plan_meta,
        ok_flag=bool(ok_flag),
        tool_msg=str(tool_msg),
        data=data,
    )

    if ok_flag:
        done("builtin", True, plan_meta)
        text = tool_msg if not data else f"{tool_msg}\n{data}"
        _record_chat_event(
            type_="builtin",
            request_id=request_id,
            ok_flag=True,
            summary=summary,
            payload=payload,
            plan_meta=plan_meta,
            endpoint="/chat",
        )
        return ok(
            "ok",
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
        ok_flag=False,
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
            ok_flag=False,
            error_type="mcp_not_allowed",
            allowed=sorted_allowed,
        )
        _record_chat_event(
            type_="mcp",
            request_id=request_id,
            ok_flag=False,
            summary=summary,
            payload=payload,
            plan_meta=plan_meta,
            endpoint="/chat",
        )
        data = {"route": "mcp", "tool_name": tool_name, "allowed": sorted_allowed}
        if plan_meta is not None:
            data["planner_meta"] = plan_meta
        return fail("不允许调用该 MCP 工具", data)

    result = mcp_client.call_tool(tool_name, args)
    if not result.get("ok"):
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
            ok_flag=False,
            error_type="mcp_run_failed",
            detail=detail,
        )
        _record_chat_event(
            type_="mcp",
            request_id=request_id,
            ok_flag=False,
            summary=summary,
            payload=payload,
            plan_meta=plan_meta,
            endpoint="/chat",
        )
        data = {"route": "mcp", "tool_name": tool_name, "detail": detail}
        if plan_meta is not None:
            data["planner_meta"] = plan_meta
        return fail("执行失败", data)

    done("mcp", True, plan_meta)
    result_data = result.get("data") or {}
    text = result_data.get("text", "")
    summary, payload_event = build_mcp_event_payload(
        route="mcp",
        tool_name=tool_name,
        plan_meta=plan_meta,
        ok_flag=True,
        result_data=result_data,
    )
    _record_chat_event(
        type_="mcp",
        request_id=request_id,
        ok_flag=True,
        summary=summary,
        payload=payload_event,
        plan_meta=plan_meta,
        endpoint="/chat",
    )

    payload_resp = {"route": "mcp", "text": text, "result": result_data}
    if plan_meta is not None:
        payload_resp["planner_meta"] = plan_meta
    return ok("ok", payload_resp)


@router.post("/chat")
def chat(body: ChatRequest):
    """非流式聊天：复用 planner 决策，返回文本 + planner_meta。"""
    request_id = new_request_id()

    def _done(
        route_kind: str,
        ok_flag: bool,
        plan_meta: dict[str, Any] | None = None,
        *,
        error: Exception | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        log_done(
            logger,
            event="chat_request_done",
            endpoint="/chat",
            request_id=request_id,
            route_kind=route_kind,
            ok=ok_flag,
            plan_meta=plan_meta,
            error=error,
            extra=extra,
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
            return _handle_mcp_non_stream(tool_name, args, manual_meta, _done, request_id)

        # 2) 默认走 planner
        try:
            mcp_tools = mcp_client.list_tools()
            plan_result = llm_client.plan(
                user_text=body.message,
                mcp_tools=mcp_tools,
                allowed_builtin_cmds=ALLOWED_BUILTIN_CMDS,
            )
        except PlanError:
            reply = llm_client.chat_simple(body.message)
            _done("chat", True, FALLBACK_CHAT_META)
            _record_chat_event(
                type_="chat",
                request_id=request_id,
                ok_flag=True,
                summary="planner fallback chat",
                payload={
                    "route": "chat",
                    "message": body.message,
                    "reply": reply,
                    "planner_meta": FALLBACK_CHAT_META,
                },
                plan_meta=FALLBACK_CHAT_META,
                endpoint="/chat",
            )
            return ok(
                "ok",
                {"route": "chat", "text": reply, "planner_meta": FALLBACK_CHAT_META},
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
        reply = llm_client.chat_simple(body.message)
        _done("chat", True, plan_meta)
        _record_chat_event(
            type_="chat",
            request_id=request_id,
            ok_flag=True,
            summary="chat reply",
            payload={
                "route": "chat",
                "message": body.message,
                "reply": reply,
                "planner_meta": plan_meta,
            },
            plan_meta=plan_meta,
            endpoint="/chat",
        )
        return ok("ok", {"route": "chat", "text": reply, "planner_meta": plan_meta})

    except httpx.HTTPStatusError as e:
        _done("llm_http_error", False, error=e)
        return fail(f"LLM 返回异常：HTTP {e.response.status_code}")
    except httpx.RequestError as e:
        _done("llm_request_error", False, error=e)
        return fail("无法连接 LLM 服务，请检查配置与网络")
    except Exception as e:
        _done("runtime_error", False, error=e)
        return fail(str(e))


def _event_stream(message: str, request_id: str):
    """
    SSE 生成器：根据意图走 mcp / builtin / chat。
    输出事件类型：delta / tool_result / done / error
    """

    def _s_done(
        route_kind: str,
        ok_flag: bool,
        plan_meta: dict[str, Any] | None = None,
        *,
        error: Exception | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        log_done(
            logger,
            event="chat_stream_done",
            endpoint="/chat/stream",
            request_id=request_id,
            route_kind=route_kind,
            ok=ok_flag,
            plan_meta=plan_meta,
            error=error,
            extra=extra,
        )

    # start
    log_done(
        logger,
        event="chat_stream_start",
        endpoint="/chat/stream",
        request_id=request_id,
        route_kind="start",
        ok=True,
    )

    try:
        parsed, mcp_err = parse_manual_mcp_or_none(message)
        if mcp_err is not None:
            _s_done(
                "mcp_parse_error",
                False,
                error=ValueError(mcp_err),
                extra={"error_type": "mcp_parse_error", "error_msg": mcp_err},
            )
            yield _mcp_sse_error("MCP 参数错误", detail=mcp_err)
            yield _over_chat()
            return

        # 1) 手动 mcp
        if parsed:
            tool_name, args = parsed
            manual_meta = {"provider_used": "manual_mcp", "fallback_used": False}
            mcp_exec = yield from _stream_mcp_tool(tool_name, args, manual_meta)

            ok_flag = _record_stream_mcp_event(request_id, tool_name, manual_meta, mcp_exec)
            _s_done(
                "mcp",
                ok_flag,
                manual_meta,
                extra=None if ok_flag else _stream_done_extra_for_mcp(mcp_exec),
            )
            return

        # 2) planner
        try:
            mcp_tools = mcp_client.list_tools()
            plan_result = llm_client.plan(
                user_text=message,
                mcp_tools=mcp_tools,
                allowed_builtin_cmds=ALLOWED_BUILTIN_CMDS,
            )
        except PlanError:
            # planner 失败：降级纯聊天流
            for chunk in llm_client.chat_streaming(message):
                yield _sse_data({"type": "delta", "text": chunk})

            _s_done("chat", True, FALLBACK_CHAT_META)
            _record_stream_chat_event(
                request_id=request_id,
                message=message,
                plan_meta=FALLBACK_CHAT_META,
                summary="planner fallback chat",
            )
            yield _over_chat()
            return

        plan, plan_meta = _unwrap_plan_result(plan_result)

        # 3) planner -> mcp
        if plan["kind"] == "mcp":
            tool_name = plan["tool_name"]
            mcp_exec = yield from _stream_mcp_tool(tool_name, plan["arguments"], plan_meta)

            ok_flag = _record_stream_mcp_event(request_id, tool_name, plan_meta, mcp_exec)
            _s_done(
                "mcp",
                ok_flag,
                plan_meta,
                extra=None if ok_flag else _stream_done_extra_for_mcp(mcp_exec),
            )
            return

        # 4) planner -> builtin
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

            ok_flag, tool_msg, data = run_tool(cmd)
            line = tool_msg
            if ok_flag:
                if data is not None and str(data).strip():
                    line = f"{tool_msg}\n{data}"
            else:
                line = f"执行失败：{tool_msg}"

            yield _sse_data({"type": "delta", "text": line})
            yield _sse_data(
                {
                    "type": "tool_result",
                    "ok": bool(ok_flag),
                    "command": cmd,
                    "data": data,
                    "planner_meta": plan_meta,
                }
            )

            _s_done(
                "builtin",
                bool(ok_flag),
                plan_meta,
                extra=None
                if ok_flag
                else {"error_type": "builtin_run_failed", "error_msg": str(tool_msg)},
            )

            summary, payload = build_builtin_event_payload(
                cmd=cmd,
                plan_meta=plan_meta,
                ok_flag=bool(ok_flag),
                tool_msg=str(tool_msg),
                data=data,
            )
            _record_chat_event(
                type_="builtin",
                request_id=request_id,
                ok_flag=bool(ok_flag),
                summary=summary,
                payload=payload,
                plan_meta=plan_meta,
                endpoint="/chat/stream",
            )
            yield _over_chat()
            return

        # 5) planner -> chat
        for chunk in llm_client.chat_streaming(message):
            yield _sse_data({"type": "delta", "text": chunk})

        _s_done("chat", True, plan_meta)
        _record_stream_chat_event(
            request_id=request_id,
            message=message,
            plan_meta=plan_meta,
            summary="chat stream reply",
        )
        yield _over_chat()

    except httpx.HTTPStatusError as e:
        _s_done("llm_http_error", False, error=e)
        yield _sse_data(
            {"type": "error", "msg": f"LLM 返回异常： HTTP {e.response.status_code}"}
        )
    except httpx.RequestError as e:
        _s_done("llm_request_error", False, error=e)
        yield _sse_data({"type": "error", "msg": "无法连接 LLM，请检查配置与网络"})
    except Exception as e:
        _s_done("runtime_error", False, error=e)
        yield _sse_data({"type": "error", "msg": str(e)})


@router.post("/chat/stream")
def chat_with_stream(body: ChatRequest):
    """SSE：多行 data: JSON；type 为 delta / done / error。"""
    request_id = new_request_id()
    return StreamingResponse(
        _event_stream(body.message, request_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )