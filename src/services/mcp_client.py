import uuid

import httpx

from src.llm.mcp_config import mcp_base, mcp_timeout


def _rpc_url() -> str:
    import os

    path = os.getenv("MCP_HTTP_PATH", "/").strip()
    if not path.startswith("/"):
        path = "/" + path
    if mcp_base == "":
        raise ValueError("未配置 MCP_SERVER_URL，请在 .env 中设置")
    return f"{mcp_base}{path}"


def mcp_initialize() -> dict:
    """发一条 MCP initialize (JSON-RPC 2.0), 成功则返回解析后的 JSON 对象。"""
    body = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "puthon-agent-learning", "version": "1.0.0"},
        },
    }

    url = _rpc_url()
    with httpx.Client(timeout=mcp_timeout, trust_env=False) as client:
        resp = client.post(url, json=body)
        resp.raise_for_status()
        data = resp.json()

    if data.get("error") is not None:
        raise RuntimeError(f"MCP 返回错误：{data['error']}")
    return data
