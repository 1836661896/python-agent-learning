from collections.abc import Awaitable, Callable

import httpx
import mcp.types as types
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client

from src.llm.mcp_config import mcp_streamable_endpoint_url, mcp_timeout
from src.types import ArgsDict

_CLIENT_INFO = types.Implementation(name="python-agent-learning", version="1.0.0")


async def _run_with_mcp_session[T](
    fn: Callable[[ClientSession], Awaitable[T]],
) -> T:
    """连上远端 MCP (Streamable HTTP)，完成 initialize 后执行 fn(session)。"""
    url = mcp_streamable_endpoint_url()
    t = float(mcp_timeout)
    # 普通请求使用 mcp_timeout；读 SSE 略放宽，避免 list/call 被过早断开。
    timeout = httpx.Timeout(connect=t, read=max(t, 120.0), write=t, pool=t)

    # 创建 HTTP 客户端
    async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
        # 创建 Streamable HTTP 客户端
        async with streamable_http_client(
            url,
            http_client=client,
            terminate_on_close=True,
        ) as (read_stream, write_stream, _get_session_id):
            # 创建 MCP 客户端会话
            async with ClientSession(
                read_stream,
                write_stream,
                client_info=_CLIENT_INFO,
            ) as session:
                # 初始化 MCP 客户端会话
                await session.initialize()
                return await fn(session)


async def mcp_list_tools_async():
    """tools/list：返回 ListToolsResult (含 tools 列表)。"""
    return await _run_with_mcp_session(lambda s: s.list_tools())


async def mcp_call_tool_async(name: str, arguments: ArgsDict | None = None):
    """tools/call： 返回 CallToolResult。"""
    return await _run_with_mcp_session(lambda s: s.call_tool(name, arguments))


def format_call_tool_result(result) -> str:
    """把 tools/call 的 CallToolResult 转化成可展示文本。"""
    if getattr(result, "isError", False):
        parts = []
        for block in result.content or []:
            if getattr(block, "type", None) == "text":
                parts.append(block.text)
        return "工具执行失败：\n" + ("\n".join(parts) if parts else "未知错误")

    parts: list[str] = []
    for block in result.content or []:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    if parts:
        return "\n".join(parts)
    sc = getattr(result, "structuredContent", None)
    if sc:
        import json

        return json.dumps(sc, ensure_ascii=False, indent=2)
    return "(工具无文本返回)"
