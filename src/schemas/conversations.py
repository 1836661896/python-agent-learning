from datetime import datetime

from pydantic import BaseModel, ConfigDict

from src.enums import ConversationKind

from .pagination import PaginationQuery


class ConversationListQuery(PaginationQuery):
    kind: ConversationKind | None = None


class ConversationListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    kind: ConversationKind
    memory_title: str
    created_at: datetime
    memory_updated_at: datetime | None
