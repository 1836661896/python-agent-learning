import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    ollama_base_url: str
    ollama_model: str
    zhipu_base_url: str
    zhipu_model: str
    zhipu_api_key: str
    timeout_sec: float


def get_llm_config() -> LLMConfig:
    return LLMConfig(
        provider=os.getenv("LLM_PROVIDER", "ollama").strip().lower(),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").strip(),
        ollama_model=os.getenv("OLLAMA_MODEL", "qwen:7b").strip(),
        zhipu_base_url=os.getenv(
            "ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"
        ).strip(),
        zhipu_model=os.getenv("ZHIPU_MODEL", "glm-4-flash").strip(),
        zhipu_api_key=os.getenv("ZHIPU_API_KEY", "").strip(),
        timeout_sec=float(os.getenv("LLM_TIMEOUT_SEC", "120")),
    )
