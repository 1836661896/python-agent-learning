from pydantic import BaseModel, Field, field_validator

from src.types import ArgsDict, RoutingMode


class ChatRequest(BaseModel):
    """聊天会话请求体。"""

    message: str = Field(..., description="消息内容")
    conversation_id: int | None = Field(
        default=None, description="会话id,若没有传则自动生成。"
    )
    routing: RoutingMode = Field(
        default="auto", description="auto=自动判别：chat/plan/mcp=强制走对应链路"
    )
    mcp_tool: str | None = Field(
        default=None, description="routing=mcp 时要调用的工具名"
    )
    mcp_arguments: ArgsDict = Field(
        default_factory=dict, description="传给 tools/call 的参数"
    )

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("消息不能为空")
        return v.strip()
