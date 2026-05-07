import logging
import os
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.models.Conversation import Conversation
from src.models.ConversationMessages import ConversationMessages, MessageRole

CONV_KIND_CHAT = "chat"

logger = logging.getLogger(__name__)


def _recent_message_rows():
    """最近最多读多少条消息（从新往旧取再反转为时间顺序）"""
    raw = os.getenv("MEMORY_RECENT_MESSAGE_ROWS", "40")
    try:
        n = int(raw)
        return max(1, n)
    except ValueError:
        return 40


def _recent_char_budget():
    """「最近对话」拼出来后总长上限，防止 prompt 太长"""
    raw = os.getenv("MEMORY_RECENT_CHAR_BUDGET", "8000")
    try:
        n = int(raw)
        return max(1, n)
    except ValueError:
        return 8000


def _refine_threshold_messages():
    """精炼触发阈值，每隔多少条消息触发一次精炼"""
    raw = os.getenv("MEMORY_REFINE_THRESHOLD_MESSAGES", "12")
    try:
        n = int(raw)
        return max(0, n)
    except ValueError:
        return 12


def _refine_context_messages():
    """精炼上下文消息条数，不要太多"""
    raw = os.getenv("MEMORY_REFINE_CONTEXT_MESSAGES", "80")
    try:
        n = int(raw)
        return max(1, n)
    except ValueError:
        return 80


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
    """写入消息行，返回消息行对象"""
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
    """消息行角色标签"""
    if role == MessageRole.user:
        return "用户"
    elif role == MessageRole.assistant:
        return "助手"
    elif role == MessageRole.system:
        return "系统"
    return str(role)


def maybe_refine_memory(
    db: Session,
    conv: Conversation,
    llm_client: Any,
) -> None:
    """精炼会话记忆，每隔多少条消息触发一次精炼"""
    try:
        t = _refine_threshold_messages()
        if t <= 0:
            return
        stmt = (
            select(func.count())
            .select_from(ConversationMessages)
            .where(ConversationMessages.conversation_id == conv.id)
        )
        N = db.scalar(stmt)
        if not isinstance(N, int):
            return
        elif N < t or N % t != 0:
            return
        rows = (
            db.execute(
                select(ConversationMessages)
                .where(ConversationMessages.conversation_id == conv.id)
                .order_by(ConversationMessages.id.desc())
                .limit(_refine_context_messages())
            )
            .scalars()
            .all()
        )
        rows = list(reversed(rows))

        lines: list[str] = []
        for m in rows:
            label = _role_label(m.role)
            lines.append(f"{label}: {m.content}")
        dialogue = "\n".join(lines).strip()
        if not dialogue:
            return
        logger.info("refine trigger conv=%s N=%s", conv.id, N)

        old = (conv.memory_summary or "").strip() or "（无）"
        intro = (
            "你是「会话摘要」助手。请根据【旧摘要】与【对话】生成一段新的中文摘要："
            "压缩细节，保留用户偏好、关键事实、未决事项；不要编造对话里没有的内容。"
            "只输出摘要正文，不要标题、不要代码围栏、不要角色前缀，"
        )
        prompt = "\n\n".join([intro, f"【旧摘要】\n{old}", f"【对话】\n{dialogue}"])

        new_text = llm_client.chat_simple(prompt).strip()
        if len(new_text) > 16000:
            new_text = new_text[:16000]

        conv.memory_summary = new_text
        conv.memory_updated_at = datetime.now(timezone.utc)
        db.add(conv)
        db.commit()

    except Exception:
        logger.exception("maybe_refine_memory failed")


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
            .limit(_recent_message_rows())
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
        if size + len(line) > _recent_char_budget:
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


def list_conversation_messages_paginated(
    db: Session,
    conversation_id: int,
    *,
    page: int = 1,
    limit: int = 20,
) -> tuple[list[ConversationMessages], int] | None:
    conv = db.get(Conversation, conversation_id)
    if conv is None:
        return None
    count_stmt = (
        select(func.count())
        .select_from(ConversationMessages)
        .where(ConversationMessages.conversation_id == conversation_id)
    )
    total = db.scalar(count_stmt)
    if total is None:
        total = 0
    total = int(total)

    offset = (page - 1) * limit

    list_stmt = (
        select(ConversationMessages)
        .where(ConversationMessages.conversation_id == conversation_id)
        .order_by(ConversationMessages.id.asc())
        .offset(offset)
        .limit(limit)
    )

    rows = list(db.execute(list_stmt).scalars().all())
    return rows, total
