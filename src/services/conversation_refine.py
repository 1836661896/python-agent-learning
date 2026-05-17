import json
import textwrap
from typing import TypedDict

from src.llm.completion import complete_chat
from src.llm.messages import build_user_message
from src.utils.json_coerce import extract_first_json_object


class RefineResult(TypedDict):
    title: str
    summary: str


def refine_memory_summary(
    old_summary: str, old_title: str, user_message: str
) -> RefineResult:
    if not user_message.strip():
        raise ValueError("用户消息不能为空")
    s = old_summary.strip()
    t = old_title.strip()
    old_summary_block = s if s else "（尚无摘要，请仅根据本轮用户消息生成摘要。）"

    old_title_block = t if t else "（尚无标题，请仅根据本轮用户消息生成标题。）"
    prompt = textwrap.dedent(f"""你是「会话整理」助手。根据【旧摘要】【旧标题】【本轮用户消息】输出更新后的会话摘要与列表用短标题。
输出要求（必须严格遵守）：
1. 只输出一个 JSON 对象，不要输出任何其它文字、不要 Markdown 代码围栏、不要注释。
2. JSON 有且仅有两个键："title" 和 "summary"，均为字符串。
3. "title"：简体中文，概括当前会话主题，长度不超过 10 个字（按字符数计，含标点则标点也算一字）；不要书名号《》包裹整句；不要换行。
4. "summary"：在旧摘要基础上合并本轮用户新信息；压缩冗余，保留用户目标与偏好、关键事实、未决事项；严格依据下方材料归纳，不要编造材料中没有的内容；是一段连续正文，不要列表符号、不要角色前缀（如「用户：」）。
5. JSON 字符串内的换行须写成 \n，双引号须转义为 \"。

【旧摘要】
{old_summary_block}

【旧标题】
{old_title_block}

【本轮用户消息】
{user_message.strip()}
""").strip()
    messages = build_user_message(prompt)
    raw = complete_chat(messages).strip()
    try:
        blob = extract_first_json_object(raw)
        data = json.loads(blob)
    except json.JSONDecodeError as e:
        raise ValueError("返回数据格式错误") from e
    if (
        not isinstance(data, dict)
        or "title" not in data
        or "summary" not in data
        or not isinstance(data["title"], str)
        or not isinstance(data["summary"], str)
    ):
        raise ValueError("返回数据格式错误")
    return {
        "title": data["title"].strip(),
        "summary": data["summary"].strip(),
    }
