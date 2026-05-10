import enum
from datetime import datetime

from sqlalchemy import DateTime, Integer, Text, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.types import ArgsDict


class ConversationKind(str, enum.Enum):
    chat = "chat"
    mcp = "mcp"
    plan = "plan"

class Conversation(Base):
    __tablename__ = "conversation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[ConversationKind] = mapped_column(
        SAEnum(ConversationKind, name="conversation_kind", native_enum=False),
        nullable=False,
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
