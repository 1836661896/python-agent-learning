from dataclasses import dataclass
from typing import Any, Iterator

from src.llm.agent_plan import plan_with_llm
from src.llm.config import get_llm_config
from src.llm.ollama_client import chat_simple as ollama_chat_simple
from src.llm.ollama_client import chat_streaming as ollama_chat_streaming
from src.llm.ollama_client import nl_to_command as ollama_nl_to_command
from src.llm.types import LLMClient
from src.llm.zhipu_client import chat_simple as zhipu_chat_simple
from src.llm.zhipu_client import chat_streaming as zhipu_chat_straming


@dataclass
class OllamaClientAdapter:
    def chat_simple(self, user_message: str) -> str:
        return ollama_chat_simple(user_message)

    def chat_stream(self, user_message) -> Iterator[str]:
        return ollama_chat_streaming(user_message)

    def plan(
        self,
        user_text: str,
        mcp_tools: list[dict[str, Any]],
        allowed_buiiltin_cmds: set[str],
    ) -> dict[str, Any]:
        return plan_with_llm(
            user_text=user_text,
            mcp_tools=mcp_tools,
            allowed_builtin_cmds=allowed_buiiltin_cmds,
        )

    def nl_to_command(self, user_text: str) -> str:
        return ollama_nl_to_command(user_text)


@dataclass
class ZhipuClientAdapter:
    def chat_simple(self, user_message: str) -> str:
        return zhipu_chat_simple(user_message)

    def chat_streaming(self, user_message: str) -> Iterator[str]:
        return zhipu_chat_straming(user_message)

    def plan(
        self,
        user_text: str,
        mcp_tools: list[dict[str, Any]],
        allowed_builtin_cmds: set[str],
    ) -> dict[str, Any]:
        # 先做“最小可用”：服用当前planner （后续再抽成 provider 无关）
        return plan_with_llm(
            user_text=user_text,
            mcp_tools=mcp_tools,
            allowed_builtin_cmds=allowed_builtin_cmds,
        )

    def nl_to_command(self, user_text: str) -> str:
        # 先复用现有实现，保证行为稳定
        return ollama_nl_to_command(user_text)


def get_llm_client() -> LLMClient:
    cfg = get_llm_config()
    if cfg.provider == "ollama":
        return OllamaClientAdapter()
    if cfg.provider == "zhipu":
        return ZhipuClientAdapter()
    raise ValueError(f"未知的 LLM_PROVIDER： {cfg.provider}")
