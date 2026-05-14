import logging

from fastapi import APIRouter, Body, Depends
from sqlalchemy import delete, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.api_response import ResponseResult, fail, success
from src.db.deps import get_db
from src.enums import ConversationKind
from src.models.conversation import Conversation
from src.models.conversation_messages import ConversationMessage
from src.schemas.conversations import (
    ConversationBatchDeleteBody,
    ConversationCreateBody,
    ConversationListItem,
    ConversationListQuery,
    ConversationMessageItem,
    ConversationMessagesQuery,
)
from src.schemas.list_result import ListResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversation", tags=["conversations"])


@router.get("/list")
def list_conversations(
    query: ConversationListQuery = Depends(), db: Session = Depends(get_db)
) -> ResponseResult[ListResult[ConversationListItem] | None]:
    """会话列表查询"""
    try:
        total_stmt = select(func.count(Conversation.id)).select_from(Conversation)
        records_stmt = select(Conversation)
        if query.kind is not None:
            total_stmt = total_stmt.where(Conversation.kind == query.kind)
            records_stmt = records_stmt.where(Conversation.kind == query.kind)
        total = db.scalar(total_stmt) or 0
        records_stmt = (
            records_stmt.order_by(Conversation.created_at.desc())
            .offset((query.page - 1) * query.limit)
            .limit(query.limit)
        )
        records = db.scalars(records_stmt).all()
        items = [ConversationListItem.model_validate(r) for r in records]
        data = ListResult(
            records=items, total=total, page=query.page, limit=query.limit
        )
        return success(
            "查询成功",
            data.model_dump(),
        )
    except SQLAlchemyError:
        logger.exception("会话列表查询失败（数据库）")
        db.rollback()
        return fail("会话列表查询失败，请稍后重试")
    except Exception:
        logger.exception("会话列表查询失败（未知错误）")
        db.rollback()
        return fail("会话列表查询失败，请稍后重试")


@router.post("/create")
def create_conversation(
    body: ConversationCreateBody = Body(), db: Session = Depends(get_db)
) -> ResponseResult[dict | None]:
    kind = body.kind or ConversationKind.chat
    try:
        conv = Conversation(
            kind=kind, memory_title="", memory_summary="", extra_json={}
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)
        return success("创建成功", {"id": conv.id})
    except SQLAlchemyError:
        logger.exception("创建新会话失败（数据库）")
        db.rollback()
        return fail("创建新会话失败。")
    except Exception:
        logger.exception("创建新会话失败（未知原因）")
        db.rollback()
        return fail("创建新会话失败。")


@router.post("/delete")
def delete_conversation_list(
    body: ConversationBatchDeleteBody, db: Session = Depends(get_db)
) -> ResponseResult[None]:
    """会话批量删除"""
    unique_ids = sorted(set(body.ids))
    try:
        stmt = select(Conversation.id).where(Conversation.id.in_(unique_ids))
        delete_ids = sorted(list(db.scalars(stmt).all()))
        if delete_ids:
            db.execute(delete(Conversation).where(Conversation.id.in_(delete_ids)))
        else:
            return fail("未找到会话，请确认数据是否正确")
        db.commit()
        return success(f"已删除选中的{len(delete_ids)}条会话")
    except SQLAlchemyError:
        logger.exception("批量删除会话失败（数据库）")
        db.rollback()
        return fail("批量删除会话失败，请稍后重试")
    except Exception:
        logger.exception("批量删除会话失败（未知错误）")
        db.rollback()
        return fail("批量删除会话失败，请稍后重试")


@router.get("/{conversation_id}/messages")
def get_conversation_messages(
    conversation_id: int,
    query: ConversationMessagesQuery = Depends(),
    db: Session = Depends(get_db),
) -> ResponseResult[ListResult[ConversationMessageItem] | None]:
    """会话历史消息查询"""
    conv = db.get(Conversation, conversation_id)
    if conv is None:
        return fail("会话不存在")
    try:
        total_stmt = select(func.count(ConversationMessage.id)).select_from(
            ConversationMessage
        )
        rows_stmt = select(ConversationMessage)
        if query.role:
            total_stmt = total_stmt.where(ConversationMessage.role == query.role)
            rows_stmt = rows_stmt.where(ConversationMessage.role == query.role)
        total_stmt = total_stmt.where(
            ConversationMessage.conversation_id == conversation_id
        )
        rows_stmt = (
            rows_stmt.where(ConversationMessage.conversation_id == conversation_id)
            .order_by(ConversationMessage.created_at.desc())
            .offset((query.page - 1) * query.limit)
            .limit(query.limit)
        )

        total = db.scalar(total_stmt) or 0
        rows = db.scalars(rows_stmt).all()
        records = [ConversationMessageItem.model_validate(r) for r in rows]
        data = ListResult(
            total=total, records=records, page=query.page, limit=query.limit
        )
        return success("查询历史会话记录成功", data.model_dump())

    except SQLAlchemyError:
        logger.exception("会话历史消息查询失败（数据库）")
        db.rollback()
        return fail("会话历史消息查询失败，请稍后重试")
    except Exception:
        logger.exception("会话历史消息查询失败（未知原因）")
        db.rollback()
        return fail("会话历史消息查询失败，请稍后重试")
