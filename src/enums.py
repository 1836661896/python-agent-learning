import enum


# 会话类型
class ConversationKind(str, enum.Enum):
    chat = "chat"
    mcp = "mcp"
    plan = "plan"


# 消息角色
class MessageRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    system = "system"
