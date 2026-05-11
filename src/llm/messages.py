from src.models.conversation_messages import ConversationMessage
from src.types import ChatMessageList


def build_user_message(text: str) -> ChatMessageList:
    return [{"role": "user", "content": text}]


def conversation_rows_to_messages(
    rows: list[ConversationMessage], memory_summary: str
) -> ChatMessageList:
    s = memory_summary.strip()
    parts: ChatMessageList = []
    if s:
        parts.append(
            {
                "role": "system",
                "content": (
                    "以下为会话摘要（压缩后的历史要点）。请结合摘要与后续对话原文作答，"
                    "不要编造摘要中未出现的事实\n\n"
                    f"【会话摘要】\n{s}\n\n"
                ),
            }
        )
    for row in rows:
        part = {"role": row.role.value, "content": row.content}
        parts.append(part)
    return parts
