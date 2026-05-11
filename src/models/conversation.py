from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.enums import ConversationKind
from src.types import ArgsDict


class Conversation(Base):
    __tablename__ = "conversation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[ConversationKind] = mapped_column(
        Enum(ConversationKind, name="conversation_kind", native_enum=False),
        nullable=False,
    )
    memory_title: Mapped[str] = mapped_column(
        String(length=20), nullable=False, default=""
    )
    memory_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    memory_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    extra_json: Mapped[ArgsDict] = mapped_column(JSONB, nullable=False, default=dict)
    owner_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
