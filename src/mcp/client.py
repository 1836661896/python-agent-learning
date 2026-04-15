import asyncio
import time
from pathlib import Path
from typing import Any

from mcp.client.stdio import StdioServerParameters, stdio_client

from mcp import ClientSession


class MCPClient:
    """最小可用 MCP 客户端：通过 stdio 连接本地 demo server。"""

    def __init__(self) -> None:
        self._python_cmd = "python"
        self._server_module = "src.mcp.demo_server"
        self._cwd = str(Path(__file__).resolve().parents[2])
        self._allowed_cache: str[str] | None = None
        self._allowed_cache_ts: float = 0.0
        self._allowed_cache_ttl: float = 30.0

    def is_ready(self) -> bool:
        return True

    async def _list_tools_async(self) -> list[dict[str, Any]]:
        server = StdioServerParameters(
            command=self._python_cmd,
            args=["-m", self._server_module],
            cwd=self._cwd,
        )
        async with stdio_client(server) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.list_tools()
                return [
                    {
                        "name": t.name,
                        "description": t.description or "",
                        "input_schema": t.inputSchema,
                    }
                    for t in result.tools
                ]

    async def _call_tool_async(
        self, tool_name: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        server = StdioServerParameters(
            command=self._python_cmd,
            args=["-m", self._server_module],
            cwd=self._cwd,
        )
        async with stdio_client(server) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, args)

                text_parts: list[str] = []
                for item in result.content:
                    if getattr(item, "type", "") == "text":
                        text_parts.append(getattr(item, "text", ""))

                return {
                    "ok": not result.isError,
                    "msg": "ok" if not result.isError else "tool error",
                    "data": {
                        "text": "\n".join(text_parts).strip(),
                        "structured": result.structuredContent,
                    },
                }

    def list_tools(self) -> list[dict[str, Any]]:
        return asyncio.run(self._list_tools_async())

    def call_tool(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        return asyncio.run(self._call_tool_async(tool_name, args))

    def allowed_tool_names(self) -> set[str]:
        """
        动态白名单（带缓存）：
        - 30秒内直接用缓存
        - 过期则调用 list_tools() 刷新
        """
        now = time.time()
        if (
            self._allowed_cache is not None
            and (now - self._allowed_cache_ts) < self._allowed_cache_ttl
        ):
            return self._allowed_cache

        tools = self.list_tools()
        names = {t["name"] for t in tools if isinstance(t.get("name"), str)}
        self._allowed_cache = names
        self._allowed_cache_ts = now
        return names
