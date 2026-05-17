"""`build_chat_model_messages` / `load_recent_conversation_rows`。"""

from unittest.mock import MagicMock

from src.enums import MessageRole
from src.services.chat_context import build_chat_model_messages


def test_build_chat_model_messages_with_summary():
    row = MagicMock()
    row.role = MessageRole.user
    row.content = "hi"

    db = MagicMock()
    scalars_result = MagicMock()
    scalars_result.all.return_value = [row]
    db.scalars.return_value = scalars_result

    msgs = build_chat_model_messages(db, 1, "摘要要点")
    assert msgs[0]["role"] == "system"
    assert "摘要要点" in msgs[0]["content"]
    assert msgs[1]["role"] == "user"


def test_build_chat_model_messages_with_extra_system():
    row = MagicMock()
    row.role = MessageRole.user
    row.content = "hi"

    db = MagicMock()
    scalars_result = MagicMock()
    scalars_result.all.return_value = [row]
    db.scalars.return_value = scalars_result

    msgs = build_chat_model_messages(
        db, 1, "", extra_system="【身份规则】逐题追问"
    )
    roles = [m["role"] for m in msgs]
    assert roles.count("system") == 1
    assert "【身份规则】" in msgs[0]["content"]
    assert msgs[-1]["role"] == "user"
