import os

mcp_base = os.getenv("MCP_SERVER_URL", "").rstrip("/")
mcp_timeout = int(os.getenv("MCP_TIMEOUT_SECONDS", "60"))
mcp_http_path = os.getenv("MCP_HTTP_PATH", "/")


def mcp_streamable_endpoint_url():
    if not mcp_base:
        raise ValueError("未配置 MCP_SERVER_URL，请先在 env 文件中正确配置。")
    path = mcp_http_path.strip()
    if not path.startswith("/"):
        path = "/" + path

    return f"{mcp_base}{path}"
