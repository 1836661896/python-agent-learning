from fastapi import APIRouter

from src.api_response import fail, success
from src.mcp import MCPClient

router = APIRouter(prefix="/mcp", tags=["mcp"])


def _mcp_fail(
    msg: str, tool_name: str = "", detail: str = "", allowed: list[str] | None = None
):
    data = {"route": "mcp"}
    if tool_name:
        data["tool_name"] = tool_name
    if detail:
        data["detail"] = detail
    if allowed is not None:
        data["allowed"] = allowed
    return fail(msg, data)


mcp_client = MCPClient()


@router.get("/health")
def mcp_health():
    """MCP 子系统健康检查"""
    return success("MCP 子系统健康检查成功", {"ready": mcp_client.is_ready()})


@router.get("/tools")
def mcp_tools():
    """查看当前 MCP 可用工具（当前占位会实现返回空列表）"""
    return success("MCP 可用工具查询成功", mcp_client.list_tools())


@router.post("/call")
def mcp_call(body: dict):
    """
    body 示例：
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
            "不允许调用该 MCP 工具", tool_name=tool_name, allowed=sorted(allowed)
        )

    try:
        result = mcp_client.call_tool(tool_name, args)
        if result.get("tool_succeeded"):
            return success("MCP 工具调用成功", result.get("data"))
        return fail(result.get("msg", "调用失败"), result.get("data"))
    except Exception as e:
        return _mcp_fail("MCP 调用异常", tool_name=tool_name, detail=str(e))
