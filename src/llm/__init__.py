"""LLM 模块统一导出入口。"""

from .llm_factory import get_llm_client

__all__ = ["get_llm_client"]
