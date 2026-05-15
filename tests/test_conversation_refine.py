"""`refine_memory_summary`：mock `complete_ollama_chat`，不访问模型。"""

from unittest.mock import MagicMock

import pytest


def test_refine_memory_summary_calls_completion(monkeypatch):
    from src.services import conversation_refine as cr

    calls: list[list] = []

    def _fake_complete(messages):
        calls.append(messages)
        return '{"title":"短标题","summary":"  新摘要一段  "}'

    monkeypatch.setattr(cr, "complete_ollama_chat", _fake_complete)

    out = cr.refine_memory_summary("旧摘要", "旧标题", "本轮用户话")
    assert out["summary"].strip() == "新摘要一段"
    assert out["title"].strip() == "短标题"
    assert len(calls) == 1
    user_content = calls[0][0]["content"]
    assert "旧摘要" in user_content
    assert "本轮用户话" in user_content
    assert "旧标题" in user_content


def test_refine_memory_summary_empty_user_raises(monkeypatch):
    from src.services import conversation_refine as cr

    monkeypatch.setattr(cr, "complete_ollama_chat", MagicMock(return_value="x"))

    with pytest.raises(ValueError, match="用户消息不能为空"):
        cr.refine_memory_summary("", "", "   ")


def test_refine_memory_summary_strips_markdown_fence(monkeypatch):
    from src.services import conversation_refine as cr

    wrapped = '```json\n{"title":"围栏内","summary":"摘要"}\n```'

    monkeypatch.setattr(cr, "complete_ollama_chat", lambda _m: wrapped)

    out = cr.refine_memory_summary("", "", "hi")
    assert out["title"] == "围栏内"
    assert out["summary"] == "摘要"


def test_refine_memory_summary_strips_prefix_prose(monkeypatch):
    from src.services import conversation_refine as cr

    wrapped = '好的，如下：\n{"title":"前缀后","summary":"摘要二"}'

    monkeypatch.setattr(cr, "complete_ollama_chat", lambda _m: wrapped)

    out = cr.refine_memory_summary("", "", "hi")
    assert out["title"] == "前缀后"
    assert out["summary"] == "摘要二"
