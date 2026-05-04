import logging
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.agent_service import run_tool
from src.api_response import fail, ok
from src.db.deps import get_db
from src.llm import get_llm_client
from src.llm.agent_plan import PlanError
from src.mcp import MCPClient
from src.routers.nl_utils import (
    ALLOWED_BUILTIN_CMDS,
    build_mcp_event_payload,
    build_mcp_fail_data,
    is_allowed_nl_command,
    parse_manual_mcp_or_none,
)
from src.models.step import AgentStep
from src.schemas import AgentNlRunRequest, AgentRunRequest
from src.services.event_services import record_event
from src.utils.datetime_fmt import format_step_ts_utc
from src.utils.obs_log import log_done, new_request_id

logger = logging.getLogger(__name__)

mcp_client = MCPClient()
llm_client = get_llm_client()

router = APIRouter(tags=["agent"])


def _record_agent_event(
    type_: str,
    request_id: str,
    ok: bool,
    summary: str,
    payload: dict[str, Any],
    plan_meta: dict[str, Any] | None = None,
) -> None:
    meta = plan_meta or {}
    record_event(
        type_=type_,
        endpoint="/agent/nl-run",
        request_id=request_id,
        ok=ok,
        provider_used=meta.get("provider_used", "unknown"),
        fallback_used=bool(meta.get("fallback_used", False)),
        summary=summary,
        payload=payload,
    )


@router.post("/agent/run")
def use_tool(body: AgentRunRequest):
    """执行结构化命令（前端直接传 text）。"""
    ok_flag, msg, data = run_tool(body.text)
    if ok_flag:
        return ok(msg, data)
    return fail(msg)


def _mcp_fail(msg: str, **kwargs):
    """统一 MCP 失败响应，data 组装复用 nl_utils。"""
    return fail(msg, build_mcp_fail_data(**kwargs))


def _run_mcp_tool(
    tool_name: str,
    args: dict,
    request_id: str,
    planner_meta: dict | None,
    done,
):
    allowed = mcp_client.allowed_tool_names()
    if tool_name not in allowed:
        sorted_allowed = sorted(allowed)
        done(
            "mcp",
            False,
            planner_meta,
            extra={"error_type": "mcp_not_allowed", "error_msg": tool_name},
        )
        summary, payload = build_mcp_event_payload(
            route="mcp",
            tool_name=tool_name,
            plan_meta=planner_meta,
            ok_flag=False,
            error_type="mcp_not_allowed",
            allowed=sorted_allowed,
        )
        _record_agent_event(
            type_="mcp",
            request_id=request_id,
            ok=False,
            summary=summary,
            payload=payload,
            plan_meta=planner_meta,
        )
        return _mcp_fail(
            "不允许调用该 MCP 工具",
            tool_name=tool_name,
            allowed=sorted_allowed,
            planner_meta=planner_meta,
        )

    mcp_result = mcp_client.call_tool(tool_name, args)
    if mcp_result.get("ok"):
        result_data = mcp_result.get("data") or {}
        done("mcp", True, planner_meta)
        summary, payload = build_mcp_event_payload(
            route="mcp",
            tool_name=tool_name,
            plan_meta=planner_meta,
            ok_flag=True,
            result_data=result_data,
        )
        _record_agent_event(
            type_="mcp",
            request_id=request_id,
            ok=True,
            summary=summary,
            payload=payload,
            plan_meta=planner_meta,
        )
        return ok(
            "执行成功",
            {
                "route": "mcp",
                "tool_name": tool_name,
                "result": result_data,
                "planner_meta": planner_meta or {},
            },
        )

    done(
        "mcp",
        False,
        planner_meta,
        extra={"error_type": "mcp_run_failed", "error_msg": str(mcp_result)},
    )
    detail = str(mcp_result)
    summary, payload = build_mcp_event_payload(
        route="mcp",
        tool_name=tool_name,
        plan_meta=planner_meta,
        ok_flag=False,
        error_type="mcp_run_failed",
        detail=detail,
    )
    _record_agent_event(
        type_="mcp",
        request_id=request_id,
        ok=False,
        summary=summary,
        payload=payload,
        plan_meta=planner_meta,
    )
    return _mcp_fail(
        "执行失败",
        tool_name=tool_name,
        detail=detail,
        planner_meta=planner_meta,
    )


@router.post("/agent/nl-run")
def run_nl_command(body: AgentNlRunRequest):
    """自然语言 -> 命令 -> 执行，给前端返回命令与执行结果。"""
    request_id = new_request_id()

    def _done(
        route_kind: str,
        ok_flag: bool,
        planner_meta: dict | None = None,
        *,
        error: Exception | None = None,
        extra: dict | None = None,
    ):
        log_done(
            logger,
            event="agent_request_done",
            endpoint="/agent/nl-run",
            request_id=request_id,
            route_kind=route_kind,
            ok=ok_flag,
            plan_meta=planner_meta,
            error=error,
            extra=extra,
        )

    try:
        # 1) 显式 mcp 语法（直接解析，不走 planner）
        parsed, mcp_err = parse_manual_mcp_or_none(body.text)
        if mcp_err is not None:
            _done(
                "mcp_parse_error",
                False,
                error=ValueError(mcp_err),
                extra={"error_type": "mcp_parse_error", "error_msg": mcp_err},
            )
            return _mcp_fail("MCP 参数错误", detail=mcp_err)

        if parsed:
            tool_name, args = parsed
            manual_meta = {"provider_used": "manual_mcp", "fallback_used": False}
            return _run_mcp_tool(tool_name, args, request_id, manual_meta, _done)

        # 2) 默认：走 JSON planner（动态读取 MCP 工具）
        try:
            mcp_tools = mcp_client.list_tools()
            plan_result = llm_client.plan(
                user_text=body.text,
                mcp_tools=mcp_tools,
                allowed_builtin_cmds=ALLOWED_BUILTIN_CMDS,
            )
        except PlanError as e:
            _done("planner_error", False, error=e)
            return fail("规划失败", {"detail": str(e), "route": "planner"})

        plan = plan_result["plan"]
        planner_meta = plan_result.get("meta", {})

        if plan["kind"] == "mcp":
            return _run_mcp_tool(
                plan["tool_name"],
                plan["arguments"],
                request_id,
                planner_meta,
                _done,
            )

        if plan["kind"] == "builtin":
            cmd = plan["command"]

            if not is_allowed_nl_command(cmd):
                _done(
                    "builtin",
                    False,
                    planner_meta,
                    extra={"error_type": "command_not_allowed", "error_msg": cmd},
                )
                return fail(
                    "当前仅允许 list/time/help/version/echo/add 命令",
                    {"command": cmd, "planner_meta": planner_meta},
                )

            ok_flag, msg, data = run_tool(cmd)
            resp_data = {
                "command": cmd,
                "result": data,
                "tool_msg": msg,
                "planner_meta": planner_meta,
            }

            if ok_flag:
                _done("builtin", True, planner_meta)
                return ok("执行成功", resp_data)

            _done(
                "builtin",
                False,
                planner_meta,
                extra={"error_type": "builtin_run_failed", "error_msg": str(msg)},
            )
            return fail("执行失败", resp_data)

        # kind == chat（nl-run 不负责纯聊天）
        _done(
            "chat_redirect",
            False,
            planner_meta,
            extra={"error_type": "route_to_chat", "error_msg": "/chat"},
        )
        return fail(
            "当前请求更适合走聊天接口： /chat",
            {"route": "chat", "planner_meta": planner_meta},
        )

    except httpx.HTTPStatusError as e:
        _done("llm_http_error", False, error=e)
        return fail(f"LLM HTTP 异常：{e.response.status_code}")
    except httpx.RequestError as e:
        _done("llm_request_error", False, error=e)
        return fail("无法连接本机 Ollama")
    except Exception as e:
        _done("runtime_error", False, error=e)
        return fail(str(e))


@router.post("/agent/mcp-run")
def run_mcp_tool(body: dict):
    """
    请求示例:
    {
      "tool_name": "ping",
      "args": {}
    }
    """
    tool_name = str(body.get("tool_name", "")).strip()
    args = body.get("args", {})

    if not tool_name:
        return _mcp_fail("tool_name 不能为空")
    if not isinstance(args, dict):
        return _mcp_fail("args 必须是对象", tool_name=tool_name)

    allowed = mcp_client.allowed_tool_names()
    if tool_name not in allowed:
        return _mcp_fail(
            "不允许调用该 MCP 工具",
            tool_name=tool_name,
            allowed=sorted(allowed),
        )

    try:
        result = mcp_client.call_tool(tool_name, args)
        if result.get("ok"):
            return ok("执行成功", result.get("data"))
        return _mcp_fail(
            result.get("msg", "执行失败"),
            tool_name=tool_name,
            detail=str(result.get("data")),
        )
    except Exception as e:
        return _mcp_fail("MCP 调用异常", tool_name=tool_name, detail=str(e))


@router.get("/agent/last-step")
def get_last_step(db: Session = Depends(get_db)):
    """返回最近一次工具执行记录。"""
    row = db.execute(
        select(AgentStep).order_by(AgentStep.step_id.desc()).limit(1)
    ).scalar_one_or_none()

    if row is None:
        return fail("暂无执行记录")

    data = {
        "tool_name": row.tool_name,
        "input_text": row.input_text,
        "ok_flag": row.ok_flag,
        "msg": row.msg,
        "timestamp": format_step_ts_utc(row.timestamp),
    }
    return ok("查询成功", data)


@router.get("/agent/steps")
def get_steps(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    """返回执行历史，默认 20 条，最多 100 条。"""
    rows = (
        db.execute(select(AgentStep).order_by(AgentStep.step_id.desc()).limit(limit))
        .scalars()
        .all()
    )
    data = [
        {
            "tool_name": r.tool_name,
            "input_text": r.input_text,
            "ok_flag": r.ok_flag,
            "msg": r.msg,
            "timestamp": format_step_ts_utc(r.timestamp),
        }
        for r in rows
    ]
    if not data:
        return fail("暂无操作历史", [])
    return ok("查询成功", data)
