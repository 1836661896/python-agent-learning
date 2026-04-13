import json
import logging
import os
from typing import Iterator

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_BASE = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen2.5:3b"
TIMEOUT_SRC = 120.0


def chat_simple(user_message: str) -> str:
    """
    调用本机 Ollama /api/chat，非流式；返回 assistant 的纯文本。
    环境变量：OLLAMA_BASE_URL / OLLAMA_MODEL（来自 .env）。
    """
    base = os.getenv("OLLAMA_BASE_URL", DEFAULT_BASE).rstrip("/")
    model = os.getenv("OLLAMA_MODEL", DEFAULT_MODEL)
    url = f"{base}/api/chat"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": user_message}],
        "stream": False,
    }

    # trust_env=False：避免本机代理变量影响 127.0.0.1 直连 Ollama。
    with httpx.Client(timeout=TIMEOUT_SRC, trust_env=False) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

    msg = data.get("message") or {}
    content = msg.get("content")
    if not isinstance(content, str) or not content.strip():
        logger.error("Ollama 响应异常 %s", data)
        raise ValueError("Ollama 返回里没有有效的 message.content")

    return content.strip()


def chat_streaming(user_message: str) -> Iterator[str]:
    """
    调用本机 Ollama /api/chat，流式：每收到一小段 assistant 文本就 yield 一次。
    环境变量：OLLAMA_BASE_URL / OLLAMA_MODEL（来自 .env）。
    """
    system_prompt = """
        你是本项目的对话助手，只能用自然语言回答。

        【当前后端真实能力（以代码为准）】
        - 查询服务器时间（time）
        - 任务列表 / 添加任务 / 删除任务（需通过系统接口，不由你假装执行）
        - 其他能力未接入前，须明确说「目前系统还不支持，只能…」

        规则：
        - 不要谎称已经创建、删除或修改了任务或数据库。
        - 用户要你执行操作时，说明应使用左侧/系统提供的任务与 Agent 功能，或等待后续自动对接。
        """
    base = os.getenv("OLLAMA_BASE_URL", DEFAULT_BASE).rstrip("/")
    model = os.getenv("OLLAMA_MODEL", DEFAULT_MODEL)
    url = f"{base}/api/chat"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "stream": True,
    }

    # trust_env=False：避免本机代理变量影响 127.0.0.1 直连 Ollama。
    with httpx.Client(timeout=TIMEOUT_SRC, trust_env=False) as client:
        with client.stream("POST", url, json=payload) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    logger.warning(
                        "Ollama 流式行无法解析为 JSON（前 200 字符）: %s", line[:200]
                    )
                    continue

                msg = data.get("message") or {}
                content = msg.get("content")
                if isinstance(content, str) and content:
                    yield content

                if data.get("done") is True:
                    break


def _fallback_command_from_text(user_text: str) -> str:
    """当 LLM 输出不稳定时，用关键词规则做兜底映射。"""
    t = user_text.strip().lower()

    # 先拦截高风险/写操作意图
    if any(k in t for k in ["删除", "删掉", "移除", "清空", "update", "修改"]):
        return "unknown"

    # 添加任务
    if any(k in t for k in ["添加", "新增", "创建"]):
        # 优先按冒号提取：例如 “添加任务：买牛奶”
        content = user_text
        if "：" in content:
            content = content.split("：", 1)[1]
        elif ":" in content:
            content = content.split(":", 1)[1]
        else:
            # 没有冒号时，尽量去掉常见前缀词
            for p in [
                "请帮我",
                "帮我",
                "请",
                "给我",
                "添加任务",
                "新增任务",
                "创建任务",
                "添加",
                "新增",
                "创建",
            ]:
                content = content.replace(p, "")
        content = content.strip().strip("。.!！")
        if content:
            return f"add {content}"
        return "unknown"

    # 时间类
    if any(k in t for k in ["时间", "几点", "time"]):
        return "time"

    # 列表类
    if any(k in t for k in ["任务列表", "任务", "列表", "list"]):
        return "list"

    # 帮助类
    if any(k in t for k in ["帮助", "help"]):
        return "help"

    # 版本类
    if any(k in t for k in ["版本", "version"]):
        return "version"

    return "unknown"


def _clean_add_payload(cmd: str) -> str:
    """规范 add 命令参数：去掉外层成对引号。"""
    if not cmd.startswith("add "):
        return cmd

    payload = cmd[4:].strip()
    if len(payload) >= 2:
        if (payload[0] == '"' and payload[-1] == '"') or (
            payload[0] == "'" and payload[-1] == "'"
        ):
            payload = payload[1:-1].strip()

    if not payload:
        return "unknown"
    return f"add {payload}"


def _normalize_command(cmd: str) -> str:
    """把模型输出归一化到受控命令集合。"""
    cmd = cmd.strip()
    if not cmd:
        return "unknown"

    lower_cmd = cmd.lower()
    if lower_cmd in {"list", "time", "help", "version"}:
        return lower_cmd

    # 保留参数原始大小写，只归一化命令词
    if lower_cmd.startswith("echo "):
        return "echo " + cmd[5:].strip()
    if lower_cmd.startswith("add "):
        normalized = "add " + cmd[4:].strip()
        return _clean_add_payload(normalized)

    return "unknown"


def nl_to_command(user_text: str) -> str:
    """自然语言转命令：优先走 LLM，失败时回退到规则映射。"""
    system_prompt = (
        "你是命令翻译器。"
        "只输出一条命令，不要解释。"
        "可用命令仅限：list/time/help/version/echo <text>/add <text>。"
        "如无法映射，输出 unknown。"
        "禁止输出多个命令、禁止使用斜杠 /、禁止解释文字。"
        "只输出一行 JSON，不要 Markdown，不要 ``` 代码块。"
        '输出格式必须严格为 {"command":"<cmd>"}。'
        '无法映射时输出 {"command":"unknown"}。'
    )

    base = os.getenv("OLLAMA_BASE_URL", DEFAULT_BASE).rstrip("/")
    model = os.getenv("OLLAMA_MODEL", DEFAULT_MODEL)
    url = f"{base}/api/chat"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        "stream": False,
    }

    with httpx.Client(timeout=TIMEOUT_SRC, trust_env=False) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

    # 模型输出被约束为一行 JSON：{"command":"..."}。
    content = (data.get("message") or {}).get("content") or ""
    try:
        if content.strip():
            cmd = _normalize_command(json.loads(content).get("command", "unknown"))
            if cmd == "unknown":
                return _fallback_command_from_text(user_text)
            return cmd
    except Exception:
        pass
    return _normalize_command(_fallback_command_from_text(user_text))
