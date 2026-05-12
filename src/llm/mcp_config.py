import os

from dotenv import load_dotenv

load_dotenv()

mcp_base = os.getenv("MCP_SERVER_URL", "").rstrip("/")
mcp_timeout = int(os.getenv("MCP_TIMEOUT_SECONDS", "60"))
