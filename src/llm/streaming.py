import json
import os
from typing import Generator

import httpx
from dotenv import load_dotenv

from src.types import ChatMessageList

load_dotenv()

base = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
model = os.getenv("OLLAMA_MODEL", "qwen:7b")


def iter_ollama_chat_chunks(messages: ChatMessageList) -> Generator[str, None, None]:
    url = f"{base}/api/chat"
    with httpx.Client(timeout=120, trust_env=False) as client:
        with client.stream(
            "POST",
            url,
            json={
                "model": model,
                "messages": messages,
                "stream": True,
            },
        ) as resp:
            resp.raise_for_status()

            for line in resp.iter_lines():
                if not line or not line.strip():
                    continue
                if line.startswith("data: "):
                    line = line.split("data: ")[-1]
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue
                message = msg.get("message") or {}
                content = message.get("content", "")
                if not content or not content.strip():
                    continue
                yield content

                if msg.get("done") is True:
                    break
