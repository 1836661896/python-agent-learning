from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class EventModel(Base):
    __tablename__ = "events"

    event_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    type: Mapped[str] = mapped_column(String(length=50), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(length=100), nullable=False)

    request_id: Mapped[str] = mapped_column(String(length=32), default=True)

    tool_succeeded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    provider_used: Mapped[str] = mapped_column(
        String(length=50), nullable=False, default="unknown"
    )
    fallback_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    summary: Mapped[str] = mapped_column(String(length=255), nullable=False, default="")

    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
