from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class Conversation(Base):
    __tablename__ = "conversation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(length=25), nullable=False)
    memory_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    memory_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    extra_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=lambda: {}
    )
    owner_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
