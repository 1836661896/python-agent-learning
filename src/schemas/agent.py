"""Agent 相关请求模型。"""

from pydantic import BaseModel, Field, field_validator


class AgentRunRequest(BaseModel):
    """结构化命令执行请求体。"""

    text: str = Field(..., description="命令内容")

    @field_validator("text")
    @classmethod
    def text_verify(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("命令不能为空")
        return v.strip()


class AgentNlRunRequest(BaseModel):
    """自然语言执行请求体。"""

    text: str = Field(..., description="自然语言输入")

    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("消息内容不能为空")
        return v.strip()
