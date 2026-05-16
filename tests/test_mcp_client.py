"""`format_call_tool_result`: 不联网。"""

from mcp.types import CallToolResult, TextContent

from src.services.mcp_client import format_call_tool_result


def test_format_call_tool_result_text():
    r = CallToolResult(content=[TextContent(type="text", text="pong")], isError=False)
    assert format_call_tool_result(r) == "pong"


def test_format_call_tool_result_error():
    r = CallToolResult(content=[TextContent(type="text", text="bad")], isError=True)
    out = format_call_tool_result(r)
    assert "失败" in out
    assert "bad" in out
