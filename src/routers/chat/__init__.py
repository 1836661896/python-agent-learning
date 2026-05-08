"""聊天路由：非流式与 SSE 流式。"""

from src.agent_service import run_tool
from src.llm.agent_plan import PlanError
from src.services.conversation_memory import (
    append_message,
    build_augmented_user_text,
    ensure_conversation,
    maybe_refine_memory,
)
from src.services.event_services import record_event

from .deps import llm_client, mcp_client
from .router import router

__all__ = [
    "router",
    "llm_client",
    "mcp_client",
    "PlanError",
    "record_event",
    "run_tool",
    "append_message",
    "build_augmented_user_text",
    "ensure_conversation",
    "maybe_refine_memory",
]
