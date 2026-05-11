import logging
import uuid
from collections.abc import Iterator
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.llm.messages import conversation_rows_to_messages
from src.llm.streaming import iter_ollama_chat_chunks
from src.models.conversation import Conversation, ConversationKind
from src.models.conversation_messages import ConversationMessage, MessageRole
from src.schemas.chat import ChatRequest
from src.types import MessageMode
from src.utils.sse_events import (
    build_delta_event,
    build_done_event,
    build_error_event,
    sse_line,
)

from .conversation_refine import refine_memory_summary

logger = logging.getLogger(__name__)


def decide_route_auto(message: str) -> MessageMode:
    return "chat"


def resolve_effective_route(body: ChatRequest) -> MessageMode:
    if body.routing != "auto":
        return body.routing
    return decide_route_auto(body.message)


def stream_chat_turn(body: ChatRequest, db: Session) -> Iterator[str]:
    """一轮流式聊天：会话 + 落库 + SSE 文本行。"""
    turn_id = uuid.uuid4().hex[:32]  # 保证不超过 VARCHAR(50)
    conv_id: int | None = None

    effective_route = resolve_effective_route(body)

    if effective_route == "chat":
        try:
            if body.conversation_id is None:
                conv = Conversation(
                    kind=ConversationKind.chat,
                    memory_summary="",
                    extra_json={},
                )
                db.add(conv)
                db.flush()
                conv_id = conv.id
            else:
                conv = db.get(Conversation, body.conversation_id)
                if conv is None:
                    yield sse_line(build_error_event("会话不存在"))
                    yield sse_line(build_done_event(None, turn_id))
                    return
                conv_id = conv.id

            db.add(
                ConversationMessage(
                    conversation_id=conv_id,
                    role=MessageRole.user,
                    content=body.message,
                    turn_id=turn_id,
                    meta={"routing": body.routing},
                )
            )
            db.flush()

            try:
                refined = refine_memory_summary(
                    conv.memory_summary or "", conv.memory_title or "", body.message
                )
                conv.memory_summary = refined["summary"].strip()[:16000]
                conv.memory_title = refined["title"].strip()[:10]
                conv.memory_updated_at = datetime.now(timezone.utc)
                db.flush()
            except Exception:
                logger.exception("refine_memory_summary failed")

            stmt = (
                select(ConversationMessage)
                .where(ConversationMessage.conversation_id == conv_id)
                .order_by(ConversationMessage.id.desc())
                .limit(40)
            )
            rows_list = db.scalars(stmt).all()
            rows = list(reversed(rows_list))

            parts: list[str] = []
            try:
                messages = conversation_rows_to_messages(
                    rows, conv.memory_summary or ""
                )
                for chunk in iter_ollama_chat_chunks(messages):
                    parts.append(chunk)
                    yield sse_line(build_delta_event(chunk))

                full = "".join(parts)
                db.add(
                    ConversationMessage(
                        conversation_id=conv_id,
                        role=MessageRole.assistant,
                        content=full,
                        turn_id=turn_id,
                        meta={},
                    )
                )
                db.commit()
            except Exception as e:
                db.rollback()
                yield sse_line(build_error_event(str(e) or "模型调用失败"))

        finally:
            if conv_id is not None:
                yield sse_line(build_done_event(conv_id, turn_id))

    elif effective_route == "plan":
        db.rollback()
        yield sse_line(build_error_event("计划链路尚未接入"))
        yield sse_line(build_done_event(None, turn_id))
    elif effective_route == "mcp":
        db.rollback()
        yield sse_line(build_error_event("mcp 链路尚未接入"))
        yield sse_line(build_done_event(None, turn_id))
