from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

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


# 会话批量删除请求体
class ConversationBatchDeleteBody(BaseModel):
    ids: list[int]

    @field_validator("ids")
    @classmethod
    def ids_not_empty(cls, v) -> list[int]:
        if not v:
            raise ValueError("至少选择一个会话")
        return v

    # 第二种写法
    # ids: list[int] = Field(
    #     ..., min_length=1, description="待删除会话主键列表；陆游里建议在 set 去重"
    # )


# 会话创建请求体
class ConversationCreateBody(BaseModel):
    kind: ConversationKind | None = None
