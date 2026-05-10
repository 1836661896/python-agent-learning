"""Chat 相关请求模型。"""

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    """聊天请求体。"""

    message: str = Field(..., description="发给模型的内容")
    conversation_id: int | None = Field(
        default=None,
        description="会话 ID：不传则服务端新建并在响应中返回",
    )

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("消息不能为空")
        return v.strip()
