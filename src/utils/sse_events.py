import json

from src.types import ArgsDict


def sse_line(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def build_delta_event(text: str) -> ArgsDict:
    delta_event = {"type": "delta", "text": text}
    return delta_event


def build_done_event(conversation_id: int | None, turn_id: str) -> ArgsDict:
    return {"type": "done", "conversation_id": conversation_id, "turn_id": turn_id}


def build_error_event(msg: str) -> ArgsDict:
    error_event = {"type": "error", "msg": msg}
    return error_event
