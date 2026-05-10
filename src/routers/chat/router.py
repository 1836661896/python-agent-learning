from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.db.session import SessionLocal
from src.schemas import ChatRequest
from src.services.chat_stream import stream_chat_turn

router = APIRouter(tags=["chat"])


@router.post("/chat/stream")
def chat_stream(body: ChatRequest):
    db = SessionLocal()

    def gen():
        try:
            yield from stream_chat_turn(body, db)
        finally:
            db.close()

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
