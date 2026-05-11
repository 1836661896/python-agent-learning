import httpx

from src.types import ChatMessageList

from .config import base, model, timeout


def complete_ollama_chat(messages: ChatMessageList) -> str:
    url = f"{base}/api/chat"
    with httpx.Client(timeout=timeout, trust_env=False) as client:
        resp = client.post(
            url, json={"model": model, "messages": messages, "stream": False}
        )
        resp.raise_for_status()

        data = resp.json()
        message = data.get("message") or {}
        assistant = message.get("content") or ""
        if not assistant or not assistant.strip():
            raise ValueError("返回数据为空")
        return assistant.strip()
