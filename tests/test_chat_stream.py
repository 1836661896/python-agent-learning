"""`stream_chat_turn`：chat / plan 占位 / mcp（mock）。"""

import json
from unittest.mock import MagicMock

from sqlalchemy import delete, select

from src.schemas.chat import ChatRequest
from src.services.chat_stream import stream_chat_turn


def _sse_payloads(chunks: list[str]) -> list[dict]:
    out: list[dict] = []
    for block in chunks:
        for line in block.splitlines():
            if line.startswith("data: "):
                out.append(json.loads(line[6:]))
    return out


def test_stream_chat_unknown_conversation():
    db = MagicMock()
    db.get.return_value = None
    body = ChatRequest(message="hi", conversation_id=999001, routing="chat")
    chunks = list(stream_chat_turn(body, db))
    ps = _sse_payloads(chunks)
    assert ps[0]["type"] == "error"
    assert ps[-1]["type"] == "done"
    assert ps[-1]["conversation_id"] is None


def test_stream_plan_placeholder_calls_rollback():
    db = MagicMock()
    body = ChatRequest(message="x", routing="plan")
    chunks = list(stream_chat_turn(body, db))
    db.rollback.assert_called_once()
    ps = _sse_payloads(chunks)
    assert ps[0]["type"] == "error"
    assert ps[-1]["type"] == "done"


def test_stream_mcp_missing_mcp_tool():
    db = MagicMock()
    body = ChatRequest(message="x", routing="mcp", mcp_tool=None)
    chunks = list(stream_chat_turn(body, db))
    ps = _sse_payloads(chunks)
    assert ps[0]["type"] == "error"
    assert "mcp_tool" in ps[0]["msg"]
    assert ps[-1]["type"] == "done"
    assert ps[-1]["conversation_id"] is None
    db.commit.assert_not_called()


def test_stream_mcp_unknown_conversation():
    db = MagicMock()
    db.get.return_value = None
    body = ChatRequest(
        message="x", conversation_id=999001, routing="mcp", mcp_tool="ping"
    )
    chunks = list(stream_chat_turn(body, db))
    ps = _sse_payloads(chunks)
    assert ps[0]["type"] == "error"
    assert "不存在" in ps[0]["msg"]
    assert ps[-1]["conversation_id"] is None
    db.commit.assert_not_called()


def test_stream_mcp_calls_tool_success(monkeypatch):
    from mcp.types import CallToolResult, TextContent

    conv = MagicMock()
    conv.id = 42
    conv.memory_summary = ""
    db = MagicMock()
    db.get.return_value = conv

    async def _fake_call(name, arguments=None):
        return CallToolResult(
            content=[TextContent(type="text", text=f"ok:{name}")], isError=False
        )

    monkeypatch.setattr("src.services.chat_stream.mcp_call_tool_async", _fake_call)

    body = ChatRequest(
        message="测",
        conversation_id=42,
        routing="mcp",
        mcp_tool="ping",
        mcp_arguments={},
    )

    chunks = list(stream_chat_turn(body, db))
    ps = _sse_payloads(chunks)
    deltas = [p for p in ps if p["type"] == "delta"]
    assert len(deltas) == 1
    assert deltas[0]["text"] == "ok:ping"
    assert ps[-1]["type"] == "done"
    assert ps[-1]["conversation_id"] == 42
    db.commit.assert_called_once()


def test_stream_chat_refine_fails_no_system_in_ollama_messages(monkeypatch):
    """精炼失败时 memory_summary 仍为空，传给流式的 messages 不应带 system。"""
    from src.models.conversation import Conversation, ConversationKind
    from src.models.conversation_messages import MessageRole

    conv = Conversation(kind=ConversationKind.chat, memory_summary="", extra_json={})
    conv.id = 1

    user_row = MagicMock()
    user_row.role = MessageRole.user
    user_row.content = "hi"

    db = MagicMock()
    db.get.return_value = conv

    scalars_result = MagicMock()
    scalars_result.all.return_value = [user_row]
    db.scalars.return_value = scalars_result

    captured: dict[str, list] = {}

    def _fail_refine(_old, _msg):
        raise RuntimeError("refine down")

    def _fake_iter(msgs):
        captured["msgs"] = msgs
        return iter(["ok"])

    monkeypatch.setattr("src.services.chat_stream.refine_memory_summary", _fail_refine)
    monkeypatch.setattr(
        "src.services.chat_stream.iter_ollama_chat_chunks",
        _fake_iter,
    )

    body = ChatRequest(message="hi", conversation_id=1, routing="chat")
    list(stream_chat_turn(body, db))

    out = captured.get("msgs", [])
    assert out and out[0]["role"] == "user"
    assert all(m.get("role") != "system" for m in out)


def test_stream_chat_persists_and_sse_order(requires_postgres, monkeypatch):
    """连真实 PostgreSQL；mock 精炼与流式分块，避免调用 Ollama。"""
    from src.db.session import SessionLocal
    from src.models.conversation import Conversation
    from src.models.conversation_messages import ConversationMessage

    monkeypatch.setattr(
        "src.services.chat_stream.refine_memory_summary",
        lambda _old_sum, _old_title, msg: {
            "title": "",
            "summary": f"REF:{msg}",
        },
    )
    ollama_msgs: dict[str, list] = {}

    def _fake_iter(msgs):
        ollama_msgs["list"] = msgs
        return iter(["aa", "bb"])

    monkeypatch.setattr(
        "src.services.chat_stream.iter_ollama_chat_chunks",
        _fake_iter,
    )

    db = SessionLocal()
    conv_id: int | None = None
    try:
        body = ChatRequest(
            message="integration hi", conversation_id=None, routing="chat"
        )
        chunks = list(stream_chat_turn(body, db))
        ps = _sse_payloads(chunks)
        deltas = [p for p in ps if p["type"] == "delta"]
        dones = [p for p in ps if p["type"] == "done"]
        assert [p["text"] for p in deltas] == ["aa", "bb"]
        assert len(dones) == 1
        conv_id = dones[0]["conversation_id"]
        assert conv_id is not None

        conv = db.get(Conversation, conv_id)
        assert conv is not None
        assert "REF:integration hi" in (conv.memory_summary or "")

        stmt = (
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conv_id)
            .order_by(ConversationMessage.id.asc())
        )
        msgs = list(db.scalars(stmt).all())
        roles = [m.role.value for m in msgs]
        assert roles == ["user", "assistant"]
        assert msgs[1].content == "aabb"

        sent = ollama_msgs.get("list", [])
        assert len(sent) >= 2
        assert sent[0]["role"] == "system"
        assert "REF:integration hi" in sent[0]["content"]
        assert sent[1]["role"] == "user"
        assert sent[1]["content"] == "integration hi"
    finally:
        if conv_id is not None:
            db.execute(
                delete(ConversationMessage).where(
                    ConversationMessage.conversation_id == conv_id
                )
            )
            db.execute(delete(Conversation).where(Conversation.id == conv_id))
            db.commit()
        db.close()
