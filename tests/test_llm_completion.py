"""`complete_ollama_chat`：mock httpx，不访问真实 Ollama。"""

from unittest.mock import MagicMock, patch

import pytest


@patch("src.llm.completion.httpx.Client")
def test_complete_ollama_chat_returns_stripped_content(mock_client_cls):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"message": {"content": "  hello world  "}}

    mock_ctx = MagicMock()
    mock_ctx.post.return_value = mock_resp
    mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
    mock_ctx.__exit__ = MagicMock(return_value=False)
    mock_client_cls.return_value = mock_ctx

    from src.llm.completion import complete_ollama_chat

    out = complete_ollama_chat([{"role": "user", "content": "hi"}])
    assert out == "hello world"
    call_kw = mock_ctx.post.call_args.kwargs["json"]
    assert call_kw["stream"] is False
    assert call_kw["messages"] == [{"role": "user", "content": "hi"}]


@patch("src.llm.completion.httpx.Client")
def test_complete_ollama_chat_empty_raises(mock_client_cls):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"message": {"content": "   "}}

    mock_ctx = MagicMock()
    mock_ctx.post.return_value = mock_resp
    mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
    mock_ctx.__exit__ = MagicMock(return_value=False)
    mock_client_cls.return_value = mock_ctx

    from src.llm.completion import complete_ollama_chat

    with pytest.raises(ValueError, match="返回数据为空"):
        complete_ollama_chat([{"role": "user", "content": "x"}])
