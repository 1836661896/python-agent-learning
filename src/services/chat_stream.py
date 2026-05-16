import logging
import uuid
from collections.abc import Iterator
from datetime import datetime, timezone

import anyio
from sqlalchemy.orm import Session

from src.llm.streaming import iter_ollama_chat_chunks
from src.models.conversation import Conversation, ConversationKind
from src.models.conversation_messages import ConversationMessage, MessageRole
from src.schemas.chat import ChatRequest
from src.services.chat_context import build_chat_model_messages
from src.services.mcp_client import format_call_tool_result, mcp_call_tool_async
from src.utils.sse_events import (
    build_delta_event,
    build_done_event,
    build_error_event,
    sse_line,
)

from .conversation_refine import refine_memory_summary
from .route_auto import AutoRouteResult, decide_route_auto

logger = logging.getLogger(__name__)


def stream_chat_turn(body: ChatRequest, db: Session) -> Iterator[str]:
    """一轮流式聊天：会话 + 落库 + SSE 文本行。"""
    turn_id = uuid.uuid4().hex[:32]  # 保证不超过 VARCHAR(50)
    conv_id: int | None = None

    auto_decision: AutoRouteResult | None = None
    if body.routing == "auto":
        auto_decision = decide_route_auto(body.message)
        effective_route = auto_decision["route"]
    else:
        effective_route = body.routing

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
                    meta={"routing": body.routing, "effective_route": effective_route},
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

            parts: list[str] = []
            try:
                messages = build_chat_model_messages(
                    db, conv_id, conv.memory_summary or ""
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
        try:
            if body.routing == "auto" and auto_decision:
                tool_name = (auto_decision.get("mcp_tool") or "").strip()
                tool_args = auto_decision.get("mcp_arguments") or {}
            else:
                tool_name = (body.mcp_tool or "").strip()
                tool_args = body.mcp_arguments or {}

            if not tool_name:
                yield sse_line(build_error_event("routing=mcp 时请传 mcp_tool"))
                yield sse_line(build_done_event(None, turn_id))
                return

            if body.conversation_id is None:
                conv = Conversation(
                    kind=ConversationKind.mcp,
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
                    meta={
                        "routing": body.routing,
                        "effective_route": effective_route,
                        "mcp_tool": tool_name,
                        "mcp_arguments": tool_args,
                    },
                )
            )
            db.flush()

            try:
                result = anyio.run(mcp_call_tool_async, tool_name, tool_args)
                text = format_call_tool_result(result)
                yield sse_line(build_delta_event(text))

                db.add(
                    ConversationMessage(
                        conversation_id=conv_id,
                        role=MessageRole.assistant,
                        content=text,
                        turn_id=turn_id,
                        meta={"mcp_tool": tool_name},
                    )
                )
                db.commit()
            except Exception as e:
                db.rollback()
                logger.exception("mcp_call_tool failed")
                yield sse_line(build_error_event(str(e) or "MCP 调用失败"))

        finally:
            if conv_id is not None:
                yield sse_line(build_done_event(conv_id, turn_id))
