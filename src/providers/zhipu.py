"""智谱 OpenAI 兼容 chat/completions（流式 + 非流式）。"""

import json
import os
from collections.abc import Generator

import httpx

from src.types import ChatMessageList


class ZhipuProvider:
    name = "zhipu"

    def __init__(self) -> None:
        self._api_key = os.getenv("ZHIPU_API_KEY", "").strip()
        self._base = os.getenv(
            "ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"
        ).rstrip("/")
        self._model = os.getenv("ZHIPU_MODEL", "glm-4-flash")
        self._timeout = int(os.getenv("LLM_TIMEOUT_SEC", "120"))

    def _headers(self) -> dict[str, str]:
        if not self._api_key:
            raise ValueError("未配置 ZHIPU_API_KEY")
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def complete(self, messages: ChatMessageList) -> str:
        url = f"{self._base}/chat/completions"
        body = {"model": self._model, "messages": messages, "stream": False}
        with httpx.Client(timeout=self._timeout, trust_env=False) as client:
            resp = client.post(url, json=body, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()

        choices = data.get("choices") or []
        if not choices:
            raise ValueError("智谱返回无 choices")
        message = choices[0].get("message") or {}
        content = (message.get("content") or "").strip()
        if not content:
            raise ValueError("智谱返回内容为空")
        return content

    def iter_chunks(self, messages: ChatMessageList) -> Generator[str, None, None]:
        url = f"{self._base}/chat/completions"
        body = {"model": self._model, "messages": messages, "stream": True}
        with httpx.Client(timeout=self._timeout, trust_env=False) as client:
            with client.stream("POST", url, json=body, headers=self._headers()) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line or not line.strip():
                        continue
                    if line.startswith("data:"):
                        line = line[5:].strip()
                    if line == "[DONE]":
                        break
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    choices = chunk.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    content = delta.get("content") or ""
                    if content:
                        yield content
