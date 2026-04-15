import httpx
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.agent_service import run_tool
from src.api_response import fail, ok
from src.db.deps import get_db
from src.llm.ollama_client import nl_to_command
from src.mcp import MCPClient
from src.mcp.commands import parse_mcp_call
from src.models.step import AgentStep
from src.schemas import AgentNlRunRequest, AgentRunRequest
from src.utils.datetime_fmt import format_step_ts_utc

mcp_client = MCPClient()

router = APIRouter(tags=["agent"])


@router.post("/agent/run")
def use_tool(body: AgentRunRequest):
    """执行结构化命令（前端直接传 text）。"""
    ok_flag, msg, data = run_tool(body.text)
    if ok_flag:
        return ok(msg, data)
    return fail(msg)


def _is_allowed_command(cmd: str) -> bool:
    # NL 到命令的白名单：先限制低风险命令，避免误触发写操作。
    if cmd in ("list", "time", "help", "version"):
        return True
    return cmd.startswith("echo ") or cmd.startswith("add ")


def _run_mcp_tool(tool_name: str, args: dict):
    mcp_result = mcp_client.call_tool(tool_name, args)
    if mcp_result.get("ok"):
        return ok(
            "执行成功",
            {
                "route": "mcp",
                "tool_name": tool_name,
                "result": mcp_result.get("data"),
            },
        )
    return fail(
        "执行失败",
        {
            "route": "mcp",
            "tool_name": tool_name,
            "detail": mcp_result,
        },
    )


@router.post("/agent/nl-run")
def run_nl_command(body: AgentNlRunRequest):
    """自然语言 -> 命令 -> 执行，给前端返回命令与执行结果。"""
    try:
        parsed = parse_mcp_call(body.text)
        if parsed:
            tool_name, args = parsed
            return _run_mcp_tool(tool_name, args)

        cmd = nl_to_command(body.text)
        if not _is_allowed_command(cmd):
            return fail(
                "当前仅允许 list/time/help/version/echo/add 命令", {"command": cmd}
            )

        ok_flag, msg, data = run_tool(cmd)
        if ok_flag:
            return ok("执行成功", {"command": cmd, "result": data, "tool_msg": msg})
        return fail("执行失败", {"command": cmd, "tool_msg": msg})
    except httpx.HTTPStatusError as e:
        return fail(f"LLM HTTP 异常：{e.response.status_code}")
    except httpx.RequestError:
        return fail("无法连接本机 Ollama")
    except Exception as e:
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
        return fail("tool_name 不能为空")
    if not isinstance(args, dict):
        return fail("args 必须是对象")
    allowed = mcp_client.allowed_tool_names()
    if tool_name not in allowed:
        return fail("不允许调用该 MCP 工具", {"allowed": sorted(allowed)})

    try:
        result = mcp_client.call_tool(tool_name, args)
        if result.get("ok"):
            return ok("执行成功", result.get("data"))
        return fail(result.get("msg", "执行失败"), result.get("data"))
    except Exception as e:
        return fail(f"MCP 调用异常： {e}")


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
