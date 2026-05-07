from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.api_response import fail, ok
from src.db.deps import get_db
from src.models.ConversationMessages import ConversationMessages
from src.services.conversation_memory import list_conversation_messages_paginated
from src.utils.datetime_fmt import format_step_ts_utc

router = APIRouter(tags=["conversations"])


def _message_row_to_item(m: ConversationMessages) -> dict:
    return {
        "id": m.id,
        "conversation_id": m.conversation_id,
        "role": m.role.value,
        "content": m.content,
        "turn_id": m.turn_id,
        "meta": m.meta or {},
        "created_at": format_step_ts_utc(m.created_at),
    }


@router.get("/conversations/{conversation_id}/messages")
def get_message_list(
    conversation_id: int,
    page: int = Query(1, ge=1, le=100),
    limit: int = Query(10, ge=5, le=50),
    db: Session = Depends(get_db),
):
    page_data = list_conversation_messages_paginated(
        db=db, conversation_id=conversation_id, page=page, limit=limit
    )
    if page_data is None:
        return fail("会话不存在")

    rows, total = page_data
    records = [_message_row_to_item(m) for m in rows]
    return ok(
        "查询成功", {"records": records, "page": page, "limit": limit, "total": total}
    )
