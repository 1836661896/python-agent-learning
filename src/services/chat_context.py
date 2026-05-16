"""从会话库构建发给聊天模型的 messages （单一入口）"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.llm.messages import conversation_rows_to_messages
from src.models.conversation_messages import ConversationMessage
from src.types import ChatMessageList

DEFAULT_CHAT_HISTORY_LIMIT = 40


def load_recent_conversation_rows(
    db: Session, conversation_id: int, *, limit: int = DEFAULT_CHAT_HISTORY_LIMIT
) -> list[ConversationMessage]:
    """按 id 倒序取最近 limit 条，再反转为时间正序。"""
    stmt = (
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conversation_id)
        .order_by(ConversationMessage.id.desc())
        .limit(limit)
    )
    rows_list = db.scalars(stmt).all()
    return list(reversed(rows_list))


def build_chat_model_messages(
    db: Session,
    conversation_id: int,
    memory_summary: str,
    *,
    history_limit: int = DEFAULT_CHAT_HISTORY_LIMIT,
) -> ChatMessageList:
    """拼装 Ollama 所需的 messages（摘要 system + 最近若干条角色对话）。"""
    rows = load_recent_conversation_rows(db, conversation_id, limit=history_limit)
    return conversation_rows_to_messages(rows, memory_summary)
