"""会话列表与会话历史 HTTP 接口（需 PostgreSQL）。"""

from sqlalchemy import delete

from src.db.session import SessionLocal
from src.enums import ConversationKind, MessageRole
from src.models.conversation import Conversation
from src.models.conversation_messages import ConversationMessage


def test_list_conversations_includes_new_rows(requires_postgres, client):
    """插入两条 chat 会话，列表接口应能查到（大 limit 首页）。"""
    db = SessionLocal()
    ids: list[int] = []
    try:
        for _ in range(2):
            c = Conversation(
                kind=ConversationKind.chat,
                memory_title="测",
                memory_summary="",
                extra_json={},
            )
            db.add(c)
            db.commit()
            db.refresh(c)
            ids.append(c.id)

        r = client.get(
            "/conversation/list",
            params={"page": 1, "limit": 200, "kind": "chat"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["code"] == 0
        data = body["data"]
        assert data["total"] >= 2
        got = {row["id"] for row in data["records"]}
        assert set(ids).issubset(got)
        for row in data["records"]:
            if row["id"] in ids:
                assert row["kind"] == "chat"
    finally:
        for cid in ids:
            db.execute(delete(Conversation).where(Conversation.id == cid))
        db.commit()
        db.close()


def test_list_conversations_kind_filter_excludes_other(requires_postgres, client):
    """kind=chat 时不应返回 plan 会话。"""
    db = SessionLocal()
    cid_chat: int | None = None
    cid_plan: int | None = None
    try:
        c1 = Conversation(
            kind=ConversationKind.chat,
            memory_title="",
            memory_summary="",
            extra_json={},
        )
        c2 = Conversation(
            kind=ConversationKind.plan,
            memory_title="",
            memory_summary="",
            extra_json={},
        )
        db.add(c1)
        db.add(c2)
        db.commit()
        db.refresh(c1)
        db.refresh(c2)
        cid_chat, cid_plan = c1.id, c2.id

        r = client.get(
            "/conversation/list",
            params={"page": 1, "limit": 500, "kind": "chat"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["code"] == 0
        got = {row["id"] for row in body["data"]["records"]}
        assert cid_chat in got
        assert cid_plan not in got
    finally:
        for cid in (cid_chat, cid_plan):
            if cid is not None:
                db.execute(delete(Conversation).where(Conversation.id == cid))
        db.commit()
        db.close()


def test_get_conversation_messages_not_found(requires_postgres, client):
    r = client.get(
        "/conversation/999001235/messages",
        params={"page": 1, "limit": 10},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["code"] != 0
    assert "不存在" in body["msg"]


def test_get_conversation_messages_pagination_and_role(requires_postgres, client):
    db = SessionLocal()
    cid: int | None = None
    try:
        c = Conversation(
            kind=ConversationKind.chat,
            memory_title="",
            memory_summary="",
            extra_json={},
        )
        db.add(c)
        db.commit()
        db.refresh(c)
        cid = c.id

        specs = [
            (MessageRole.user, "u1", "turn-a"),
            (MessageRole.assistant, "a1", "turn-a"),
            (MessageRole.user, "u2", "turn-b"),
        ]
        for role, content, tid in specs:
            m = ConversationMessage(
                conversation_id=cid,
                role=role,
                content=content,
                turn_id=tid,
                meta={},
            )
            db.add(m)
        db.commit()

        r = client.get(
            f"/conversation/{cid}/messages",
            params={"page": 1, "limit": 10},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["code"] == 0
        data = body["data"]
        assert data["total"] == 3
        assert len(data["records"]) == 3

        r2 = client.get(
            f"/conversation/{cid}/messages",
            params={"page": 1, "limit": 10, "role": "user"},
        )
        assert r2.json()["code"] == 0
        d2 = r2.json()["data"]
        assert d2["total"] == 2
        assert len(d2["records"]) == 2
        assert all(x["role"] == "user" for x in d2["records"])

        r3 = client.get(
            f"/conversation/{cid}/messages",
            params={"page": 1, "limit": 2},
        )
        d3 = r3.json()["data"]
        assert d3["total"] == 3
        assert len(d3["records"]) == 2
    finally:
        if cid is not None:
            db.execute(
                delete(ConversationMessage).where(
                    ConversationMessage.conversation_id == cid
                )
            )
            db.execute(delete(Conversation).where(Conversation.id == cid))
            db.commit()
        db.close()
