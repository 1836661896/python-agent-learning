from typing import Any

from src.db.session import SessionLocal
from src.models.event import EventModel


def record_event(
    *,
    type_: str,
    endpoint: str,
    request_id: str,
    tool_succeeded: bool,
    provider_used: str = "unknown",
    fallback_used: bool = False,
    summary: str = "",
    payload: dict[str, Any] | None = None,
) -> None:
    with SessionLocal() as db:
        row = EventModel(
            type=type_,
            endpoint=endpoint,
            request_id=request_id,
            tool_succeeded=tool_succeeded,
            provider_used=provider_used,
            fallback_used=fallback_used,
            summary=summary,
            payload=payload or {},
        )
        db.add(row)
        db.commit()
