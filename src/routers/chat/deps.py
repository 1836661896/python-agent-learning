"""聊天路由依赖：LLM 客户端与 MCP 客户端。"""
from src.llm import get_llm_client
from src.mcp import MCPClient

llm_client = get_llm_client()
mcp_client = MCPClient()
