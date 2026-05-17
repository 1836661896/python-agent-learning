"""`complete_chat`：mock provider，不访问真实 LLM。"""

from unittest.mock import MagicMock

import pytest


def test_complete_chat_returns_stripped_content(monkeypatch):
    mock_provider = MagicMock()
    mock_provider.complete.return_value = "  hello world  "

    monkeypatch.setattr(
        "src.llm.completion.get_provider",
        lambda _name=None: mock_provider,
    )

    from src.llm.completion import complete_chat

    out = complete_chat([{"role": "user", "content": "hi"}])
    assert out == "  hello world  "
    mock_provider.complete.assert_called_once_with(
        [{"role": "user", "content": "hi"}]
    )


def test_complete_chat_uses_fallback_on_primary_error(monkeypatch):
    primary = MagicMock()
    primary.complete.side_effect = RuntimeError("down")
    fallback = MagicMock()
    fallback.complete.return_value = "ok"

    def _get_provider(name):
        if name == "ollama":
            return fallback
        return primary

    monkeypatch.setattr("src.llm.completion.config.llm_provider", "zhipu")
    monkeypatch.setattr("src.llm.completion.config.llm_fallback_provider", "ollama")
    monkeypatch.setattr("src.llm.completion.get_provider", _get_provider)

    from src.llm.completion import complete_chat

    assert complete_chat([{"role": "user", "content": "x"}]) == "ok"
