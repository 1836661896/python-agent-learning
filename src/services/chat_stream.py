import logging
import uuid
from collections.abc import Iterator
from datetime import datetime, timezone

import anyio
from sqlalchemy.orm import Session

from src.llm import config
from src.llm.messages import build_user_message
from src.llm.streaming import iter_chat_chunks
from src.models.conversation import Conversation, ConversationKind
from src.models.conversation_messages import ConversationMessage, MessageRole
from src.schemas.chat import ChatRequest
from src.services.agent_presets import build_preset_system_content, is_known_preset
from src.services.chat_context import build_chat_model_messages
from src.services.mcp_client import format_call_tool_result, mcp_call_tool_async
from src.utils.sse_events import (
    build_delta_event,
    build_done_event,
    build_error_event,
    build_tool_call_event,
    build_tool_result_event,
    sse_line,
)

from .conversation_refine import refine_memory_summary
from .route_auto import AutoRouteResult, decide_route_auto

logger = logging.getLogger(__name__)


def _resolve_preset_id(body: ChatRequest, conv: Conversation | None) -> str | None:
    """请求 preset 优先，否则读会话 extra_json.preset。"""
    if is_known_preset(body.preset):
        return (body.preset or "").strip()
    if conv is not None:
        ej = conv.extra_json if isinstance(conv.extra_json, dict) else {}
        p = ej.get("preset")
        if is_known_preset(p):
            return str(p).strip()
    return None


def _apply_preset_to_conv(conv: Conversation, preset_id: str | None) -> None:
    if not preset_id:
        return
    ej = dict(conv.extra_json) if isinstance(conv.extra_json, dict) else {}
    ej["preset"] = preset_id
    conv.extra_json = ej


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
                extra_json: dict = {}
                if is_known_preset(body.preset):
                    extra_json["preset"] = (body.preset or "").strip()
                elif body.routing == "auto" and auto_decision:
                    ap = auto_decision.get("preset")
                    if is_known_preset(ap):
                        extra_json["preset"] = str(ap).strip()
                conv = Conversation(
                    kind=ConversationKind.chat,
                    memory_summary="",
                    extra_json=extra_json,
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
                if is_known_preset(body.preset):
                    _apply_preset_to_conv(conv, (body.preset or "").strip())
                    db.flush()
                elif body.routing == "auto" and auto_decision:
                    ap = auto_decision.get("preset")
                    if is_known_preset(ap):
                        _apply_preset_to_conv(conv, str(ap).strip())
                        db.flush()

            db.add(
                ConversationMessage(
                    conversation_id=conv_id,
                    role=MessageRole.user,
                    content=body.message,
                    turn_id=turn_id,
                    meta={
                        "routing": body.routing,
                        "effective_route": effective_route,
                        "preset": _resolve_preset_id(body, conv),
                    },
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
                preset_id = _resolve_preset_id(body, conv)
                extra_sys = (
                    build_preset_system_content(preset_id) if preset_id else None
                )
                messages = build_chat_model_messages(
                    db, conv_id, conv.memory_summary or "", extra_system=extra_sys
                )
                for chunk in iter_chat_chunks(messages):
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
                yield sse_line(build_tool_call_event(tool_name, tool_args))
                result = anyio.run(mcp_call_tool_async, tool_name, tool_args)
                mcp_raw = format_call_tool_result(result)
                yield sse_line(build_tool_result_event(tool_name, mcp_raw))

                if config.mcp_reply_via_llm:
                    prompt = (
                        f"用户问题：{body.message.strip()}\n\n"
                        f"工具「{tool_name}」返回：\n{mcp_raw}\n"
                        "请用简短自然的中文回答用户，说明工具执行结果。"
                        "不要编造返回中没有的内容。"
                    )
                    parts: list[str] = []
                    for chunk in iter_chat_chunks(build_user_message(prompt)):
                        parts.append(chunk)
                        yield sse_line(build_delta_event(chunk))
                    full = "".join(parts)
                    assistant_meta = {"mcp_tool": tool_name, "mcp_raw": mcp_raw}
                else:
                    yield sse_line(build_delta_event(mcp_raw))
                    full = mcp_raw
                    assistant_meta = {"mcp_tool": tool_name}

                db.add(
                    ConversationMessage(
                        conversation_id=conv_id,
                        role=MessageRole.assistant,
                        content=full,
                        turn_id=turn_id,
                        meta=assistant_meta,
                    )
                )
                db.commit()
            except Exception as e:
                db.rollback()
                logger.exception("mcp_call_tool failed")
                err_msg = str(e) or "MCP 调用失败"
                yield sse_line(
                    build_tool_result_event(tool_name, err_msg, is_error=True)
                )
                yield sse_line(build_error_event(err_msg))

        finally:
            if conv_id is not None:
                yield sse_line(build_done_event(conv_id, turn_id))
