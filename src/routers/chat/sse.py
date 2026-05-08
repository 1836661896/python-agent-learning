"""聊天路由 SSE 流式：根据意图走 mcp / builtin / chat 。"""

import json
from collections.abc import Generator

from .deps import llm_client, mcp_client
from .types import ArgsDict


def _sse_data(obj: ArgsDict) -> str:
    """单条 SSE： data 后为 JSON，结尾空行。"""
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


def _delta_dict(text: str) -> ArgsDict:
    """delta 事件的 JSON 字典。"""
    return {"type": "delta", "text": text}


def _over_chat() -> str:
    """统一结束事件。"""
    return _sse_data({"type": "done"})


def _mcp_sse_error(
    msg: str,
    detail: str = "",
    tool_name: str = "",
    allowed: list[str] | None = None,
) -> str:
    payload: ArgsDict = {"type": "error", "msg": msg, "route": "mcp"}
    if detail:
        payload["detail"] = detail
    if tool_name:
        payload["tool_name"] = tool_name
    if allowed is not None:
        payload["allowed"] = allowed
    return _sse_data(payload)


def _mcp_tool_fail_sse(
    msg: str,
    tool_name: str,
    error_type: str,
    *,
    detail: str = "",
    allowed: list[str] | None = None,
) -> Generator[str, None, ArgsDict]:
    """产出错误 SSE + done，并以生成器返回值给出执行摘要（与外层 return 一致）。"""
    yield _mcp_sse_error(msg, tool_name=tool_name, detail=detail, allowed=allowed)
    yield _over_chat()
    payload: ArgsDict = {
        "tool_succeeded": False,
        "tool_name": tool_name,
        "error_type": error_type,
    }
    if detail:
        payload["detail"] = detail
    if allowed is not None:
        payload["allowed"] = allowed
    return payload


def _yield_sse_chat_stream(augmented: str) -> Generator[str, None, str]:
    """流式输出 chat delta SSE, return 拼接后的全文。"""
    parts: list[str] = []
    for chunk in llm_client.chat_streaming(augmented):
        parts.append(chunk)
        yield _sse_data(_delta_dict(chunk))
    return "".join(parts)


def _stream_mcp_tool(
    tool_name: str,
    args: ArgsDict,
    plan_meta: ArgsDict | None = None,
) -> Generator[str, None, ArgsDict]:
    """
    流式执行 MCP 工具：
    - 产出 SSE 文本
    - return 执行摘要（tool_succeeded/error/result），供外层统一写日志与事件
    """
    allowed = mcp_client.allowed_tool_names()
    if tool_name not in allowed:
        sorted_allowed = sorted(allowed)
        return (
            yield from _mcp_tool_fail_sse(
                "不允许调用该 MCP 工具",
                tool_name,
                "mcp_not_allowed",
                allowed=sorted_allowed,
            )
        )

    result = mcp_client.call_tool(tool_name, args)
    if not result.get("tool_succeeded"):
        detail = str(result)
        return (
            yield from _mcp_tool_fail_sse(
                result.get("msg", "tool error"),
                tool_name,
                "mcp_run_failed",
                detail=detail,
            )
        )

    data = result.get("data") or {}
    yield _sse_data(_delta_dict(data.get("text", "")))
    yield _sse_data(
        {
            "type": "tool_result",
            "tool_succeeded": True,
            "route": "mcp",
            "tool_name": tool_name,
            "data": data,
            "planner_meta": plan_meta or {},
        }
    )
    yield _over_chat()
    return {"tool_succeeded": True, "tool_name": tool_name, "result": data}
