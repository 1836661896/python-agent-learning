import logging
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api_response import fail, ok
from src.db.deps import get_db
from src.llm import get_llm_client
from src.models.DocSession import DocSession
from src.models.DocSessionMessages import DocSessionMessages
from src.schemas import DocSessionCreate, DocSessionMessageCreate
from src.services.docx_itinerary import build_itinerary_docx, resolve_output_file
from src.services.event_services import record_event
from src.utils.obs_log import new_request_id

router = APIRouter(tags=["doc_sessions"])

logger = logging.getLogger(__name__)

MOCK_ASSISTANT_REPLY = (
    "收到。为帮你列明天的行程，请先补充这几点：\n"
    "1) 明天必须完成的事有哪些？\n"
    "2) 大概几点起床？\n"
    "3) 有没有固定时间点（会议/出行）？\n"
    "4) 还有哪些想做但非必须的事？"
)


DOC_SESSION_SYSTEM = """【角色】
你是帮助用户整理「明天行程/日程」的助手，用中文交流。

【任务】
通过多轮对话追问：必做事项、起床时间、固定时段、可选项等；信息仍不足就继续问，不要一次写满全天细节，
已出现的对话在下方，请接着上下文回复，不要重复已确认的事实。

【约束】
只作为对话助手回答，不要假装已经生成 Word 或保存了文件（除非产品明确说已接好）。
回复要简洁、分点可接受，不要冗长编故事。
"""


def _build_doc_session_prompt(
    history: list[DocSessionMessages],
) -> str:
    """
    把多轮消息拼成一段，交给当前 chat_simple （单条 user 文本）使用。
    """
    lines: list[str] = [DOC_SESSION_SYSTEM.strip(), "", "--- 对话开始 ---", ""]
    for m in history:
        who = "用户" if m.role == "user" else "助手"
        lines.append(f"{who}: {m.content}")
        lines.append("")
    lines.append("--- 对话结束 ---")
    lines.append("请只输出你作为助手的 **下一条** 回复，不要加角色前缀。")
    return "\n".join(lines).strip()


def _messages_to_document_text(rows: list) -> str:
    lines: list[str] = []
    for m in rows:
        who = "用户" if m.role == "user" else "助手"
        lines.append(f"{who}: {m.content}")
        lines.append("")
    return "\n".join(lines).strip()


@router.post("/doc-sessions")
def create_doc_session(body: DocSessionCreate, db: Session = Depends(get_db)):
    try:
        session = DocSession()
        # 若以后 body.doc_kind 要落 slots_json 或新列，在这里赋值
        db.add(session)
        db.commit()
        db.refresh(session)
        return ok(
            "创建成功",
            {
                "session_id": session.id,
                "phase": session.phase,
                "slots_json": session.slots_json,
                "created_at": session.created_at.isoformat(),
            },
        )

    except Exception:
        logger.exception("创建文档会话失败")
        db.rollback()
        return fail("创建失败")


@router.get("/doc-sessions/{session_id}")
def get_doc_session(session_id: int, db: Session = Depends(get_db)):
    row = db.get(DocSession, session_id)
    if row is None:
        return fail("会话不存在")
    return ok(
        "查询成功",
        {
            "session_id": row.id,
            "phase": row.phase,
            "slots_json": row.slots_json,
            "output_path": row.output_path,
            "created_at": row.created_at.isoformat(),
        },
    )


@router.post("/doc-sessions/{session_id}/messages")
def append_doc_session_message(
    session_id: int, body: DocSessionMessageCreate, db: Session = Depends(get_db)
):
    session = db.get(DocSession, session_id)
    if session is None:
        return fail("会话不存在")

    try:
        user_msg = DocSessionMessages(
            session_id=session_id, role="user", content=body.content
        )
        db.add(user_msg)
        db.flush()

        history = (
            db.execute(
                select(DocSessionMessages)
                .where(DocSessionMessages.session_id == session_id)
                .order_by(DocSessionMessages.id.asc())
            )
            .scalars()
            .all()
        )

        prompt = _build_doc_session_prompt(history)
        llm = get_llm_client()

        try:
            reply_text = llm.chat_simple(prompt)
            if not reply_text or not reply_text.strip():
                raise ValueError("LLM 返回空文本")
        except Exception:
            logger.exception("会话文档：LLM 调用失败，使用降级文案")
            reply_text = MOCK_ASSISTANT_REPLY

        assistant_msg = DocSessionMessages(
            session_id=session_id,
            role="assistant",
            content=reply_text.strip(),
        )
        db.add(assistant_msg)
        db.commit()
        db.refresh(user_msg)
        db.refresh(assistant_msg)

        return ok(
            "发送成功",
            {
                "session_id": session_id,
                "phase": session.phase,
                "user_message_id": user_msg.id,
                "assistant_message_id": assistant_msg.id,
                "assistant_reply": assistant_msg.content,
            },
        )

    except Exception:
        logger.exception("写入会话消息失败")
        db.rollback()
        return fail("发送失败")


@router.get("/doc-sessions/{session_id}/messages")
def list_doc_session_messages(session_id: int, db: Session = Depends(get_db)):
    session = db.get(DocSession, session_id)
    if session is None:
        return fail("会话不存在")

    rows = (
        db.execute(
            select(DocSessionMessages)
            .where(DocSessionMessages.session_id == session_id)
            .order_by(DocSessionMessages.id.asc())
        )
        .scalars()
        .all()
    )

    items = [
        {
            "id": r.id,
            "role": r.role,
            "content": r.content,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]

    return ok("查询成功", {"session_id": session_id, "items": items})


@router.post("/doc-sessions/{session_id}/generate")
def generate_doc_session_docx(session_id: int, db: Session = Depends(get_db)):
    row = db.get(DocSession, session_id)
    if row is None:
        return fail("会话不存在")

    request_id = new_request_id()
    try:
        history = (
            db.execute(
                select(DocSessionMessages)
                .where(DocSessionMessages.session_id == session_id)
                .order_by(DocSessionMessages.id.asc())
            )
            .scalars()
            .all()
        )
        body_text = _messages_to_document_text(history) or "（无对话内容）"
        title = f"行程整理 · 会话 {session_id}"

        filename = build_itinerary_docx(
            session_id=session_id, title=title, body_text=body_text
        )
        row.output_path = filename
        row.phase = "doc_generated"  # collecting 区分，且长度 < 25
        db.add(row)
        db.commit()
        db.refresh(row)

        record_event(
            type_="doc_session",
            endpoint="/doc-sessions/generate",
            request_id=request_id,
            ok=True,
            provider_used="docx",
            summary=f"itinerary docx: session_id={session_id}",
            payload={"session_id": session_id, "filename": filename},
        )

        return ok(
            "已生成",
            {
                "session_id": session_id,
                "phase": row.phase,
                "file_name": filename,
                "download": f"/doc-sessions/{session_id}/download",
            },
        )
    except Exception:
        logger.exception("生成 docx 失败")
        db.rollback()
        record_event(
            type_="doc_session",
            endpoint="/doc-sessions/generate",
            request_id=request_id,
            ok=False,
            provider_used="docx",
            summary="docx generate failed",
            payload={"session_id": session_id, "error_type": "docx_write_failed"},
        )
        return fail("生成失败")


@router.get("/doc-sessions/{session_id}/download")
def download_doc_session_docx(session_id: int, db: Session = Depends(get_db)):
    row = db.get(DocSession, session_id)
    if row is None or not row.output_path:
        return fail("没有可下载的文件，请先生成")

    try:
        path = resolve_output_file(row.output_path)
    except (OSError, ValueError, FileNotFoundError):
        logger.exception("下载路径解析失败")
        return fail("文件不存在或路径无效")

    return FileResponse(
        path=path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=Path(path).name,
    )
