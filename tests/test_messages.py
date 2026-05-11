"""`conversation_rows_to_messages`：摘要与对话行拼装。"""

from unittest.mock import MagicMock

from src.llm.messages import conversation_rows_to_messages


def _fake_row(role_value: str, content: str):
    row = MagicMock()
    row.role.value = role_value
    row.content = content
    return row


def test_conversation_rows_no_summary_only_dialogue():
    rows = [_fake_row("user", "hello")]
    msgs = conversation_rows_to_messages(rows, "")
    assert len(msgs) == 1
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"] == "hello"


def test_conversation_rows_whitespace_summary_same_as_empty():
    rows = [_fake_row("user", "x")]
    msgs = conversation_rows_to_messages(rows, "   \n")
    assert len(msgs) == 1
    assert msgs[0]["role"] == "user"


def test_conversation_rows_prepends_system_when_summary():
    rows = [_fake_row("user", "hi")]
    msgs = conversation_rows_to_messages(rows, "  要点一  ")
    assert len(msgs) == 2
    assert msgs[0]["role"] == "system"
    assert "要点一" in msgs[0]["content"]
    assert "【会话摘要】" in msgs[0]["content"]
    assert msgs[1]["role"] == "user"
    assert msgs[1]["content"] == "hi"
