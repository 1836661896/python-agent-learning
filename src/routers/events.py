from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.api_response import ok
from src.db.deps import get_db
from src.models.event import EventModel
from src.utils.datetime_fmt import format_step_ts_utc

router = APIRouter(tags=["events"])


@router.get("/events")
def list_events(
    limit: int = Query(20, ge=1, le=100),
    page: int = Query(1, ge=1),
    event_type: str | None = Query(None, alias="type"),
    command: str | None = Query(None),
    status: Literal["all", "success", "failed"] = Query("all"),
    db: Session = Depends(get_db),
):
    conds: list = []

    if event_type is not None:
        conds.append(EventModel.type == event_type)

    if status == "success":
        conds.append(EventModel.ok.is_(True))
    elif status == "failed":
        conds.append(EventModel.ok.is_(False))

    if command is not None:
        conds.append(EventModel.payload["command"].astext == command)

    count_stmt = select(func.count()).select_from(EventModel)
    if conds:
        count_stmt = count_stmt.where(*conds)

    total = db.scalar(count_stmt)
    if total is None:
        total = 0

    offset = (page - 1) * limit
    list_stmt = (
        select(EventModel)
        .order_by(EventModel.event_id.desc())
        .offset(offset)
        .limit(limit)
    )

    if conds:
        list_stmt = list_stmt.where(*conds)

    rows = db.execute(list_stmt).scalars().all()

    records = [
        {
            "event_id": r.event_id,
            "type": r.type,
            "endpoint": r.endpoint,
            "request_id": r.request_id,
            "ok": r.ok,
            "provider_used": r.provider_used,
            "fallback_used": r.fallback_used,
            "summary": r.summary,
            "payload": r.payload,
            "created_at": format_step_ts_utc(r.created_at),
        }
        for r in rows
    ]

    return ok(
        "查询成功", {"records": records, "page": page, "limit": limit, "total": total}
    )
