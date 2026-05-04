from pydantic import BaseModel, Field, field_validator


class DocSessionCreate(BaseModel):
    """创建文档会话：字段可按产品在扩展"""

    doc_kind: str | None = Field(None, max_length=50, description="如 itinerary")


class DocSessionMessageCreate(BaseModel):
    """用户在某会话里发一句话。"""

    content: str = Field(..., description="用户消息正文")

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("消息不能为空")
        return v.strip()
