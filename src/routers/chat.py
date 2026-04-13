import json
import logging

import httpx
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.agent_service import run_tool
from src.api_response import fail, ok
from src.llm.intent import classify_route
from src.llm.ollama_client import chat_simple, chat_streaming, nl_to_command
from src.schemas import ChatRequest

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])


@router.post("/chat")
def chat_with_ollama(body: ChatRequest):
    """代理调用本机 Ollama，供前端聊天面板使用。"""
    try:
        reply = chat_simple(body.message)
        return ok("ok", reply)
    except httpx.HTTPStatusError as e:
        logger.error("Ollama HTTP 错误")
        return fail(f"Ollama 返回异常：HTTP {e.response.status_code}")
    except httpx.RequestError:
        logger.exception("无法连接 Ollama")
        return fail("无法连接 Ollama，请确认服务已启动（默认 http://127.0.0.1:11434）")
    except Exception as e:
        logger.exception("Ollama 调用失败")
        return fail(str(e))


def _sse_data(obj: dict) -> str:
    """单条 SSE： data 后为JSON，结尾空行。"""
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


def _is_allowed_nl_command(cmd: str) -> bool:
    if cmd in ("list", "time", "help", "version"):
        return True
    return cmd.startswith("echo ") or cmd.startswith("add ")


def _event_stream(message: str):
    """
    SSE 生成器：根据意图走「纯聊天流式」或「自然语言转命令再 run_tool」。
    时间类型：delta（征文）/toole_result（结构化结果，可选给前端刷新列表）/done/error。
    """
    try:
        # ① 规则路由： 不调用大模型；只决定走 chat 还是 agent
        route = classify_route(message)

        if route == "agent":
            # ② 与 自然语言 → 一条命令（内部可能调LLM，失败会走 fallback）
            cmd = nl_to_command(message)

            # ③ 与 POST /agent/nl_run 一致的白名单，避免误执行
            if cmd == "unknown" or not _is_allowed_nl_command(cmd):
                yield _sse_data(
                    {
                        "type": "delta",
                        "text": (
                            "当前无法把这句话安全的转成可执行命令，或不在允许范围内。"
                            f"（解析结果：{cmd}；允许： list/time/help/version/echo.../add...）"
                        ),
                    }
                )
                yield _sse_data({"type": "done"})
                return

            # ④ 执行工具；结果写入步骤历史等 由 agent_service 负责
            ok_flag, tool_msg, data = run_tool(cmd)

            # ⑤ 给用户看的纯文本（兼容之处理 delta 的前端）
            if ok_flag:
                line = tool_msg
                if data is not None and str(data).strip():
                    line = f"{tool_msg}\n{data}"
            else:
                line = f"执行失败：{tool_msg}"

            yield _sse_data({"type": "delta", "text": line})

            # ⑥ 结构化一包：便于前端收到后 invalidate tasks / steplist （可选）
            yield _sse_data(
                {
                    "type": "tool_result",
                    "ok": ok_flag,
                    "command": cmd,
                    "msg": tool_msg,
                    "data": data,
                }
            )
            yield _sse_data({"type": "done"})
            return

        # ⑦ 闲聊： Ollama 流式输出，多段 delta
        for chunk in chat_streaming(message):
            yield _sse_data({"type": "delta", "text": chunk})
        yield _sse_data({"type": "done"})

    except httpx.HTTPStatusError as e:
        logger.error("Ollama HTTP 错误（流式）")
        yield _sse_data(
            {"type": "error", "msg": f"Ollama 返回异常： HTTP {e.response.status_code}"}
        )
    except httpx.RequestError:
        logger.exception("无法连接 Ollama（流式）")
        yield _sse_data(
            {
                "type": "error",
                "msg": "无法连接 Ollama，请确认服务已启动（默认 http://127.0.0.1:11434）",
            }
        )
    except Exception as e:
        logger.exception("流式处理失败")
        yield _sse_data({"type": "error", "msg": str(e)})


@router.post("/chat/stream")
def chat_with_stream(body: ChatRequest):
    """SSE：多行 data: JSON；type 为 delta / done / error。"""
    return StreamingResponse(
        _event_stream(body.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
