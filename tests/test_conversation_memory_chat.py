"""
会话记忆相关测试：mock 数据库 Session + mock conversation_memory，
专注断言 planner 收到 augmented、响应含 conversation_id、append_message 调用次数。
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import src.routers.chat as chat_module
from src.api import app
from src.db.deps import get_db
from src.models.ConversationMessages import MessageRole


@pytest.fixture
def mock_session():
    return MagicMock()


@pytest.fixture
def client(mock_session):
    """用假的 Session 代替 Depends(get_db)， 避免测试必须连 PostgreSQL。"""

    def _fake_db():
        yield mock_session

    app.dependency_overrides[get_db] = _fake_db
    with TestClient(app) as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def memory_mock(monkeypatch):
    """伪造会话行 + 记录 append_message 调用。"""
    conv = MagicMock()
    conv.id = 42
    conv.memory_summary = ""

    calls: list[dict] = []

    def _ensure(db, conversation_id):
        return conv

    def _append(db, conversation_id, role, content, turn_id, meta=None):
        calls.append(
            {
                "conversation_id": conversation_id,
                "role": role,
                "content": content,
                "turn_id": turn_id,
                "meta": meta or {},
            }
        )
        return MagicMock()

    monkeypatch.setattr(chat_module, "ensure_conversation", _ensure)
    monkeypatch.setattr(chat_module, "append_message", _append)

    def _build(db, c, last_user_message):
        return f"AUGMENTED:{last_user_message}"

    monkeypatch.setattr(chat_module, "build_augmented_user_text", _build)

    return conv, calls


def text_chat_plan_returns_conversation_id_and_uses_augmented(
    client, monkeypatch, memory_mock
):
    _, calls = memory_mock

    captured_plan = {}

    def _plan(user_text, mcp_tools, allowed_builtin_cmds):
        captured_plan["user_text"] = user_text
        return {
            "plan": {"kind": "chat", "answer_hint": ""},
            "meta": {"provider_used": "mocl", "fallback_used": False},
        }

    monkeypatch.setattr(chat_module.llm_client, "plan", _plan)
    monkeypatch.setattr(
        chat_module.llm_client,
        "chat_simple",
        lambda msg: "助手回复",
    )

    resp = client.post("/chat", json={"message": "你好"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["conversation_id"] == 42
    assert body["data"]["test"] == "助手回复"

    assert captured_plan["user_text"].startswith("AUGMENTED:")
    # user + assistant 各一次
    assert len(calls) == 2
    assert calls[0]["role"] == MessageRole.user
    assert calls[0]["content"] == "你好"
    assert calls[1]["role"] == MessageRole.assistant
    assert calls[1]["content"] == "助手回复"


def test_chat_planneror_fallback_uses_augmented(client, monkeypatch, memory_mock):
    _, calls = memory_mock

    def _raise(*aygs, **kwargs):
        raise chat_module.PlanError("x")

    monkeypatch.setattr(chat_module.llm_client, "plan", _raise)
    monkeypatch.setattr(
        chat_module.llm_client,
        "chat_simple",
        lambda msg: ("success") if msg.startswith("AUGMENTED:") else "BAD",
    )

    resp = client.post("/chat", json={"message": "测试"})
    assert resp.status_code == 200
    assert resp.json()["data"]["text"] == "success"
    assert len(calls) == 2


def test_chat_stream_accumulates_reply(monkeypatch, memory_mock, mock_session):
    _, calls = memory_mock

    monkeypatch.setattr(
        chat_module.llm_client,
        "plan",
        lambda **kwargs: {
            "plan": {"kind": "chat"},
            "meta": {"provider_used": "mock", "fallback_used": False},
        },
    )
    monkeypatch.setattr(
        chat_module.llm_client, "chat_streaming", lambda msg: iter(["aa", "bb"])
    )

    app.dependency_overrides[get_db] = lambda: (yield mock_session)
    try:
        with TestClient(app) as client:
            with client.stream(
                "POST", "/chat/stream", json={"message": "流式"}
            ) as resp:
                assert resp.status_code == 200
                raw = "".join(resp.iter_text())
            assert "aa" in raw and "bb" in raw
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert len(calls) >= 2
    assert calls[-1]["role"] == MessageRole.assistant
    assert calls[-1]["content"] == "aabb"
