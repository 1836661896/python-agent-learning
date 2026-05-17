from collections.abc import Generator
from typing import Protocol

from src.types import ChatMessageList


class ChatProvider(Protocol):
    """各厂商都实现： 非流式 + 流式。"""

    name: str

    def complete(self, messages: ChatMessageList) -> str: ...
    def iter_chunks(self, messages: ChatMessageList) -> Generator[str, None, None]: ...
