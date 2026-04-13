from typing import Literal

Route = Literal["chat", "agent"]


def classify_route(user_text: str) -> Route:
    """
    规则路由（不调用 LLM）：
    - agent：更像要执行后端已有命令（time / list / add / help / version / echo 等）；
    - chat：其它闲聊、解释、或不适合自动走工具的情况。
    """
    t = user_text.strip()
    if not t:
        return "chat"

    low = t.lower()

    # 删除/修改类：不自动走 agent，避免误执行；可交给聊天说明或用前端删任务
    if any(k in t for k in ("删除", "删掉", "移除", "清空", "修改")):
        return "chat"
    # 时间（中文；英文避免误伤 lifetime 等，只认独立 time）
    if any(k in t for k in ("几点", "现在几点", "时间", "日期", "今天几号")):
        return "agent"
    if low == "time" or low.startswith("time "):
        return "agent"
    # 任务列表（不用单独「任务」二字，避免「任务好难」误判）
    if any(k in t for k in ("任务列表", "列出任务", "有哪些任务", "显示任务")):
        return "agent"
    if low == "list" or low.startswith("list "):
        return "agent"
    # 添加任务
    if any(k in t for k in ("添加", "新增", "创建")):
        return "agent"
    if "帮助" in t or low == "help" or low.startswith("help "):
        return "agent"
    if "版本" in t or low == "version" or low.startswith("version "):
        return "agent"
    if low.startswith("echo "):
        return "agent"
    return "chat"


if __name__ == "__main__":
    samples = [
        "现在几点了",
        "列出任务",
        "帮我添加任务：买牛奶",
        "你好，介绍一下你自己",
        "删除第一个任务",
        "任务好难啊",
    ]
    for s in samples:
        print(repr(s), "->", classify_route(s))
