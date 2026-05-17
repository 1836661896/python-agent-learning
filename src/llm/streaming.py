import logging
from typing import Generator

from src.providers import get_provider
from src.types import ChatMessageList

from . import config

logger = logging.getLogger(__name__)


def iter_chat_chunks(messages: ChatMessageList) -> Generator[str, None, None]:
    primary = config.llm_provider
    fallback = config.llm_fallback_provider

    def _run(name: str) -> Generator[str, None, None]:
        yield from get_provider(name).iter_chunks(messages)

    try:
        yield from _run(primary)
    except Exception:
        if fallback and fallback != primary:
            logger.warning("LLM provider %s failed, fallback to %s", primary, fallback)
            yield from _run(fallback)
        else:
            raise
