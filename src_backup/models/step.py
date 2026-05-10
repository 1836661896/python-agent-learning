from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class AgentStep(Base):
    __tablename__ = "agent_steps"

    step_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tool_name: Mapped[str] = mapped_column(String(length=255), nullable=False)
    input_text: Mapped[str] = mapped_column(String(255), nullable=False)
    tool_succeeded: Mapped[bool] = mapped_column(Boolean, nullable=False)
    msg: Mapped[str] = mapped_column(String(50), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
