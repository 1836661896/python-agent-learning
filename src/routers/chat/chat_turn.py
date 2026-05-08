from typing import Any

from sqlalchemy.orm import Session

from src.models.ConversationMessages import MessageRole
from src.schemas import ChatRequest

from .pkg import _chat_pkg
from .types import ArgsDict

FALLBACK_CHAT_META = {"provider_used": "planner_fallback_chat", "fallback_used": True}


def _prepare_planner_user_turn(
    db: Session,
    body: ChatRequest,
    request_id: str,
) -> tuple[Any, str, str]:
    """校验会话、写入用户消息并提交；返回 (conv, turn_id, augmented)。"""
    turn_id = request_id
    p = _chat_pkg()
    conv = p.ensure_conversation(db, body.conversation_id)
    augmented = p.build_augmented_user_text(db, conv, body.message)
    p.append_message(
        db,
        conv.id,
        MessageRole.user,
        body.message,
        turn_id,
        meta={"request_id": request_id},
    )
    db.commit()
    return conv, turn_id, augmented


def _unwrap_plan_result(
    plan_result: ArgsDict,
) -> tuple[ArgsDict, ArgsDict]:
    """统一拆包 planner 返回：{'plan': ..., 'meta': ...}。"""
    plan = plan_result["plan"]
    plan_meta = plan_result.get("meta") or {}
    return plan, plan_meta


def _builtin_rejected_message(cmd: str) -> str:
    """统一被拒绝提示文案，避免非流式/流式写两份。"""
    return (
        "当前无法把这句话安全的转成可执行命令，或不在允许范围内。"
        f"（解析结果：{cmd}；允许： list/time/help/version/echo.../add...）"
    )
