from typing import Any, Iterator, Protocol


class LLMClient(Protocol):
    def chat_simple(self, user_message: str) -> str: ...

    def chat_streaming(self, user_message: str) -> Iterator[str]: ...

    def plan(
        self,
        user_text: str,
        mcp_tools: list[dict[str, Any]],
        allowed_builtin_cmds: set[str],
    ) -> dict[str, Any]: ...

    def nl_to_command(self, user_text: str) -> str: ...
