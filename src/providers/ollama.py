import json
import os
from collections.abc import Generator

import httpx

from src.types import ChatMessageList


class OllamaProvider:
    name = "ollama"

    def __init__(self) -> None:
        self._base = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
        self._model = os.getenv("OLLAMA_MODEL", "qwen:7b")
        self._timeout = int(os.getenv("LLM_TIMEOUT_SEC", "120"))

    def complete(self, messages: ChatMessageList) -> str:
        url = f"{self._base}/api/chat"
        with httpx.Client(timeout=self._timeout, trust_env=False) as client:
            resp = client.post(
                url, json={"model": self._model, "messages": messages, "stream": False}
            )
            resp.raise_for_status()
            data = resp.json()

        message = data.get("message") or {}
        content = (message.get("content") or "").strip()
        if not content:
            raise ValueError("Ollama 返回内容为空")
        return content

    def iter_chunks(self, messages: ChatMessageList) -> Generator[str, None, None]:
        url = f"{self._base}/api/chat"
        with httpx.Client(timeout=self._timeout, trust_env=False) as client:
            with client.stream(
                "POST",
                url,
                json={"model": self._model, "messages": messages, "stream": True},
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line or not line.strip():
                        continue
                    if line.startswith("data: "):
                        line = line.split("data: ", 1)[-1]

                    try:
                        msg = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    message = msg.get("message") or {}
                    content = message.get("content", "")
                    if content:
                        yield content
                    if msg.get("done") is True:
                        break
