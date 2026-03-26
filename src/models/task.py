from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class TaskModel(Base):
  __tablename__ = "tasks"

  task_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  task_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)