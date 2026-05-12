from datetime import datetime

from pydantic import BaseModel, ConfigDict

from src.enums import ConversationKind, MessageRole
from src.types import ArgsDict

from .pagination import PaginationQuery


# 会话列表查询
class ConversationListQuery(PaginationQuery):
    kind: ConversationKind | None = None


# 会话列表项
class ConversationListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    kind: ConversationKind
    memory_title: str
    created_at: datetime
    memory_updated_at: datetime | None


# 会话消息列表查询
class ConversationMessagesQuery(PaginationQuery):
    role: MessageRole | None = None


# 会话消息列表项
class ConversationMessageItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    conversation_id: int
    role: MessageRole
    content: str
    turn_id: str
    meta: ArgsDict
    created_at: datetime
