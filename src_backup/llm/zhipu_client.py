import json
import logging
import os
from typing import Iterator

import httpx
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

DEFAULT_ZHIPU_BASE = "https://open.bigmodel.cn/api/paas/v4"
DEFAULT_ZHIPU_MODEL = "glm-4-flash"
TIMEOUT_SEC = 120.0


def _merge_stream_piece(acc_text: str, piece: str) -> tuple[str, str]:
    if not piece:
        return acc_text, ""

    # 服务端返回“完整累计文本”
    if piece.startswith(acc_text):
        new_part = piece[len(acc_text) :]
        return piece, new_part

    # 完全重复片段
    if acc_text.endswith(piece):
        return acc_text, ""

    # 处理部分重叠
    max_k = min(len(acc_text), len(piece))
    overlap = 0
    for k in range(max_k, 0, -1):
        if acc_text.endswith(piece[:k]):
            overlap = k
            break

    new_part = piece[overlap:]
    return acc_text + new_part, new_part


def chat_simple(user_message: str) -> str:
    """
    调用智谱 chat completions（非流式），返回 assistant 的纯文本。
    依赖环境变量：
      - ZHIPU_API_KEY
      - ZHIPU_BASE_URL（建议填根地址，例如https://open.bigmodel.cn/api/paas/v4）
      - ZHIPU_MODEL
    """
    api_key = os.getenv("ZHIPU_API_KEY", "").strip()
    if not api_key:
        raise ValueError("缺少 ZHIPU_API_KEY， 请先在 .env 中配置")

    base_url = os.getenv("ZHIPU_BASE_URL", DEFAULT_ZHIPU_BASE).rstrip("/")
    model = os.getenv("ZHIPU_MODEL", DEFAULT_ZHIPU_MODEL)

    url = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": user_message},
        ],
        "stream": False,
    }

    try:
        with httpx.Client(timeout=TIMEOUT_SEC, trust_env=False) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        # 常见 401/403 key 问题，429 限流
        raise ValueError(f"智谱 HTTP 异常： {e.response.status_code}") from e
    except httpx.RequestError as e:
        raise ValueError("无法连接智谱服务，请检查网络或 BASE_URL") from e

    try:
        content = data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error("智谱返回结构异常： %s", data)
        raise ValueError("智谱返回里没有有效的 message.content") from e

    if not isinstance(content, str) or not content.strip():
        logger.error("智谱返回内容为空： %s", data)
        raise ValueError("智谱返回内容为空")

    return content.strip()


def chat_streaming(user_message: str) -> Iterator[str]:
    """
    调用智谱 chat completions（流式），每次 yield 一段文本增量。
    """
    api_key = os.getenv("ZHIPU_API_KEY", "").strip()
    if not api_key:
        raise ValueError("缺少 ZHIPU_API_KEY，请先在 .env 中配置")

    base_url = os.getenv("ZHIPU_BASE_URL", DEFAULT_ZHIPU_BASE).rstrip("/")
    model = os.getenv("ZHIPU_MODEL", DEFAULT_ZHIPU_MODEL)

    url = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": user_message}],
        "stream": True,
    }

    try:
        with httpx.Client(timeout=TIMEOUT_SEC, trust_env=False) as client:
            with client.stream("POST", url, headers=headers, json=payload) as resp:
                resp.raise_for_status()

                acc_text = ""

                for raw_line in resp.iter_lines():
                    line = (raw_line or "").strip()
                    if not line:
                        continue

                    # SSE 行格式通常是： data: {...}
                    if not line.startswith("data:"):
                        continue

                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        break

                    try:
                        obj = json.loads(data_str)
                    except json.JSONDecodeError:
                        logger.warning("智谱流式行 JSON 解析失败： %s", data_str[:200])
                        continue

                    # 智谱兼容 OpenAI 风格增量： choices[0].delta.content
                    delta = ((obj.get("choices") or [{}])[0].get("delta") or {}).get(
                        "content"
                    )
                    if isinstance(delta, str) and delta:
                        acc_text, out = _merge_stream_piece(acc_text, delta)
                        if out:
                            yield out

    except httpx.HTTPStatusError as e:
        raise ValueError(f"智谱流式 HTTP 异常：{e.response.status_code}") from e
    except httpx.RequestError as e:
        raise ValueError("无法连接智谱流式服务，请检查网络或 BASE_URL") from e
