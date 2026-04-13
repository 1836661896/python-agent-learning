"""LLM 相关能力导出。"""

from .ollama_client import chat_simple, nl_to_command

__all__ = ["chat_simple", "nl_to_command"]
