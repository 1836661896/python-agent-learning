from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.Conversation import Conversation
from src.models.ConversationMessages import ConversationMessages, MessageRole

CONV_KIND_CHAT = "chat"

# 最近最多读多少条消息（从新往旧取再反转为时间顺序）
RECENT_MESSAGE_ROWS = 40
# 「最近对话」拼出来后总长上限，防止 prompt 太长
RECENT_CHAR_BUDGET = 8000


def ensure_conversation(
    db: Session, conversation_id: int | None, kind: str = CONV_KIND_CHAT
) -> Conversation:
    """
    有 id：从数据库取会话，不存在则抛错（由路由层转成「会话不存在」）。
    无 id：新建一条会话并提交，用于「首次对话不带头绪 id」。
    """
    if conversation_id is not None:
        row = db.get(Conversation, conversation_id)
        if row is None:
            raise ValueError("会话不存在")
        return row
    conv = Conversation(kind=kind)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def append_message(
    db: Session,
    conversation_id: int,
    role: MessageRole,
    content: str,
    turn_id: str,
    meta: dict[str, Any] | None = None,
) -> ConversationMessages:
    row = ConversationMessages(
        conversation_id=conversation_id,
        role=role,
        content=content,
        turn_id=turn_id,
        meta=meta if meta is not None else {},
    )
    db.add(row)
    db.flush()
    return row


def _role_label(role: MessageRole) -> str:
    if role == MessageRole.user:
        return "用户"
    elif role == MessageRole.assistant:
        return "助手"
    elif role == MessageRole.system:
        return "系统"
    return str(role)


def build_augmented_user_text(
    db: Session, conv: Conversation, last_user_message: str
) -> str:
    """
    在尚未写入本轮用户消息之前调用：
    用已有摘要 + 已有消息行，拼成一段交给 chat_simple / streaming 的长文本。
    """
    summary = (conv.memory_summary or "").strip()

    rows = (
        db.execute(
            select(ConversationMessages)
            .where(ConversationMessages.conversation_id == conv.id)
            .order_by(ConversationMessages.id.desc())
            .limit(RECENT_MESSAGE_ROWS)
        )
        .scalars()
        .all()
    )
    # 数据库按 id 从新到旧取的，翻回「从早到晚」
    rows = list(reversed(rows))

    lines: list[str] = []
    size = 0
    for m in rows:
        label = _role_label(m.role)
        line = f"{label}: {m.content}"
        if size + len(line) > RECENT_CHAR_BUDGET:
            break
        lines.append(line)
        size += len(line) + 1

    recent = "\n".join(lines).strip()

    parts: list[str] = []
    if summary:
        parts.append(f"【历史摘要】\n{summary}")
    if recent:
        parts.append(f"【最近对话】\n{recent}")
    parts.append(f"【用户当前输入】\n{last_user_message.strip()}")
    return "\n\n".join(parts)
