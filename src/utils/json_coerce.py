import json


def strip_markdown_fence(text: str) -> str:
    text = (text or "").strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    if lines:
        lines = lines[1:]  # 去掉 ```json
    while lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def extract_first_json_object(raw: str) -> str:
    """去掉常见围栏后，只取第一个可解析的 JSON 对象子串。"""
    text = strip_markdown_fence(raw)
    if not text:
        raise ValueError("返回数据为空")
    start = text.find("{")
    if start == -1:
        raise ValueError("未找到 JSON 对象")
    _, end = json.JSONDecoder().raw_decode(text, start)
    return text[start:end]
