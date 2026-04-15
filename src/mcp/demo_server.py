from datetime import datetime

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("demo-server")


@mcp.tool()
def ping() -> str:
    """最小连通性测试工具"""
    return "pong"


@mcp.tool()
def now() -> str:
    """返回当前时间"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


if __name__ == "__main__":
    # 使用 stdio 传输，方便本地子进程方式接入
    mcp.run(transport="stdio")
