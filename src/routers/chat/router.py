from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.db.deps import get_db
from src.db.session import SessionLocal
from src.schemas import ChatRequest
from src.utils.obs_log import new_request_id

from .logic import chat_endpoint, event_stream

router = APIRouter(tags=["chat"])


@router.post("/chat")
def chat(body: ChatRequest, db: Session = Depends(get_db)):
    """非流式聊天：复用 planner 决策，返回文本 + planner_meta。"""
    return chat_endpoint(body, db)


@router.post("/chat/stream")
def chat_with_stream(body: ChatRequest):
    """SSE：多行 data：JSON；type 为 delta / done / error。"""
    request_id = new_request_id()
    db = SessionLocal()
    return StreamingResponse(
        event_stream(body, request_id, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
