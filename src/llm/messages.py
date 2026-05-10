from src.models.conversation_messages import ConversationMessage
from src.types import ChatMessageList


def build_user_message(text: str) -> ChatMessageList:
    return [{"role": "user", "content": text}]


def conversation_rows_to_messages(rows: list[ConversationMessage]) -> ChatMessageList:
    parts: ChatMessageList = []
    for row in rows:
        part = {"role": row.role.value, "content": row.content}
        parts.append(part)
    return parts
