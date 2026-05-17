import logging

from src.providers import get_provider
from src.types import ChatMessageList

from . import config

logger = logging.getLogger(__name__)


def complete_chat(messages: ChatMessageList) -> str:
    primary = config.llm_provider
    fallback = config.llm_fallback_provider

    def _run(name: str) -> str:
        return get_provider(name).complete(messages)

    try:
        return _run(primary)
    except Exception:
        if fallback and fallback != primary:
            logger.warning("LLM provider %s failed, fallback to %s", primary, fallback)
            return _run(fallback)
        raise
