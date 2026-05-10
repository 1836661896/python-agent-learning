from typing import Any, Literal

# 字典类型
type ArgsDict = dict[str, Any]

# 用户消息
type ChatMessageList = list[ArgsDict]

# 消息模式
type MessageMode = Literal["chat", "mcp", "plan"]

# 路由模式
type RoutingMode = Literal["auto", "chat", "mcp", "plan"]
