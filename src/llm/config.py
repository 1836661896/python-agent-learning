import os


def _env_bool(name: str, default: bool = False) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


# 通用
timeout = int(os.getenv("LLM_TIMEOUT_SEC", "120"))


# 供应商
llm_provider = os.getenv("LLM_PROVIDER", "ollama").strip().lower()
llm_fallback_provider = os.getenv("LLM_FALLBACK_PROVIDER", "").strip().lower()

mcp_reply_via_llm = _env_bool("MCP_REPLY_VIA_LLM", default=False)
