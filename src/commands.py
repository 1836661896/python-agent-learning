"""命令行与 Agent 工具模块。

职责概览：
    - 维护内存中的任务列表 ``TASK_LIST``，并与 ``tasks.json`` 同步；
    - 通过 ``Agent`` + ``Tool`` 将用户输入路由到具体工具（list/add/delete 等）；
    - ``run_tool`` 供 API 与命令行共用；``handle_command`` 仅负责命令行交互（quit、非法前缀、打印）。

约定：
    - 工具统一返回 ``(ok: bool, msg: str, data: Any)``；
    - ``ok`` 为 False 时，命令行打印 ``msg``；为 True 时按 ``data`` 类型决定如何展示（见 ``_print_tool_result``）。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable
from collections import deque

from sqlalchemy import select

from src.db.session import SessionLocal
from src.models.task import TaskModel
from src.models.step import AgentStep

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 常量与任务数据
# ---------------------------------------------------------------------------

# 各命令的「说明文案」，供 help 工具返回并在命令行展示
HELP_MESSAGE = {
    "help": "展示当前可输入的指令",
    "version": "展示当前版本信息",
    "quit": "退出",
    "echo": "回显后面的内容",
    "list": "展示当前任务列表",
    "add": "添加任务到任务列表",
    "delete": "删除任务列表中的任务",
    "time": "展示当前时间",
    "其他": "直接展示出来",
}

# 程序固定话术：欢迎语、提示、版本号、错误提示等（键与代码里 show_message 传入的键一致）
SYSTEM_MESSAGE = {
    "welcome": "欢迎来到 Python Agent 学习项目！",
    "hint": "输入命令，输入 quit 退出。",
    "quit": "再见！",
    "version": "1.0.0",
    "invalid_command": "未知命令格式，请直接输入文本或输入 help 查看帮助",
}


def adjust_command(command: str) -> str:
    """从整条命令里取出「第一个词之后」的文本。

    示例：
        ``"add 买牛奶"`` → ``"买牛奶"``；``"echo"`` 单独一词 → ``""``。

    用于 ``add`` / ``delete`` / ``echo`` 等「动词 + 参数」形式，参数里可以含空格
    （用 ``split`` 只拆第一个空格会丢信息，因此先 ``split(" ")`` 再 ``join`` 后半段）。

    Returns:
        第一个词之后的字符串；若整行只有一个词则返回空字符串。
    """
    parts = command.split(" ")
    # 先处理「只有一词」并 return，剩余逻辑写在 if 外，少一层 else（guard clause 常见写法）
    if len(parts) == 1:
        return ""
    return " ".join(parts[1:])


# ---------------------------------------------------------------------------
# Agent：Tool / Step / 匹配器 / 工具实现
# ---------------------------------------------------------------------------


@dataclass
class Tool:
    """描述一个可调用工具（命令行与 API 共用的一套逻辑）。

    Attributes:
        name: 工具标识，用于日志与 Step 记录。
        match: 判断当前用户输入是否应由本工具处理；多个工具时**按 TOOLS 列表顺序**第一个命中的执行。
        run: 执行工具；返回三元组 ``(是否成功, 说明信息, 附加数据)``，供 API JSON 或命令行打印。
    """

    name: str
    match: Callable[[str], bool]
    run: Callable[[str], tuple[bool, str, Any]]


@dataclass
class Step:
    """单次工具调用的快照，用于 ``logger.info`` 排查问题。

    Attributes:
        tool_name: 命中的工具名；未命中任意工具时为 ``"unknown"``。
        input_text: 用户原始输入（已 ``strip`` 后传入 Agent 的文本）。
        ok_flag: 工具返回的成功标志。
        msg: 工具返回的说明字符串。
        timestamp: 命中并执行完毕时的时间戳字符串。
    """

    tool_name: str
    input_text: str
    ok_flag: bool
    msg: str
    timestamp: str


def format_step(step: Step) -> str:
    """把 Step 格式化成一行人类可读的日志文本。

    使用两个相邻的 f-string，Python 会在编译时自动拼接为**一个**字符串，
    中间无换行；源码里换行只是为了不超过行宽、方便阅读。
    """
    return (
        f"调用{step.tool_name} 执行{step.input_text}，执行结果：{step.ok_flag}，"
        f"返回信息：{step.msg}；执行时间：{step.timestamp}"
    )

def _record_step(self, step: Step) -> None:
    self.last_step = step
    self.step_history.append(step)
    with SessionLocal() as db:
        try:
            agent_step = AgentStep(
                tool_name = step.tool_name,
                input_text = step.input_text,
                ok_flag = step.ok_flag,
                msg = step.msg,
            )
            db.add(agent_step)
            db.commit()
        except Exception as e:
            db.rollback()


class Agent:
    """在用户输入上依次尝试各工具的 ``match``，命中则 ``run`` 并返回三元组。"""

    def __init__(self, tools: list[Tool]) -> None:
        self.tools = tools
        self.last_step: Step | None = None
        self.step_history: list[Step] = deque(maxlen=50)

    def run_text(self, text: str) -> tuple[bool, str, Any]:
        """对一行输入执行工具路由。

        流程：
            1. 空串 → 失败，提示「请输入命令」；
            2. 按 ``self.tools`` 顺序遍历，``match`` 为真则 ``run`` 并返回；
            3. 全部未命中 → 失败，「未知命令」，并记录 ``last_step`` 为 unknown。

        Returns:
            ``(ok, msg, data)``，与各 ``tool_*`` 返回值含义一致。
        """
        text = text.strip()
        if not text:
            logger.info("未输入命令")
            return False, "请输入命令", None

        for tool in self.tools:
            # 先构造 Step 骨架；只有 match 成功才填时间戳并写入 last_step
            step = Step(
                tool_name=tool.name,
                input_text=text,
                ok_flag=False,
                msg="",
                timestamp="",
            )
            if tool.match(text):
                ok_flag, msg, data = tool.run(text)
                step.ok_flag = ok_flag
                step.msg = msg
                step.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                _record_step(self, step)
                logger.info(format_step(step))
                return ok_flag, msg, data

        # 没有任何工具匹配：不要误以为「成功无数据」
        _record_step(self, Step(
            tool_name="unknown",
            input_text=text,
            ok_flag=False,
            msg="未知命令",
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ))
        logger.info("未知命令： %s", text)
        return False, "未知命令", None


# --- match_*：仅负责「这条输入是否归我管」，逻辑要简单，避免副作用 ---


def match_list(cmd: str) -> bool:
    """整行等于 ``list`` 时才是列表命令（避免误伤其它以 list 开头的词）。"""
    return cmd == "list"


def match_add(cmd: str) -> bool:
    """以 ``add`` 开头，后接空格与任务内容。"""
    return cmd.startswith("add")


def match_delete(cmd: str) -> bool:
    """以 ``delete`` 开头，后接任务 id。"""
    return cmd.startswith("delete")


def match_echo(cmd: str) -> bool:
    """以 ``echo`` 开头，后接要回显的文本。"""
    return cmd.startswith("echo")


def match_time(cmd: str) -> bool:
    """整行等于 ``time``。"""
    return cmd == "time"


def match_help(cmd: str) -> bool:
    """整行等于 ``help``。"""
    return cmd == "help"


def match_version(cmd: str) -> bool:
    """整行等于 ``version``。"""
    return cmd == "version"


# --- tool_*：真正读写 TASK_LIST 或返回展示数据；与 API 共用，因此用返回值而非 print ---


def tool_list(cmd: str) -> tuple[bool, str, Any]:
    """返回当前任务列表引用（成功时 data 为 ``TASK_LIST``）。"""
    # return True, "ok", TASK_LIST
    with SessionLocal() as db:
        row = db.execute(select(TaskModel).order_by(TaskModel.task_id.asc())).scalars().all()
        data = [{"task_id": r.task_id, "task_name": r.task_name} for r in row]
        return True, "ok", data
    



def tool_add(cmd: str) -> tuple[bool, str, Any]:
    """解析 ``add …``，追加任务并 ``save_tasks``。

    任务 id：在现有最大 ``task_id`` 上加 1；列表为空则从 1 开始。
    同名任务拒绝重复添加。
    """
    task_content = adjust_command(cmd)
    if not task_content:
        return False, "未输入任务内容", None
    with SessionLocal() as db:
        if db.execute(
            select(TaskModel).where(TaskModel.task_name == task_content)
        ).scalar_one_or_none():
            return False, "任务已存在", None
        
        task = TaskModel(task_name = task_content)
        db.add(task)
        db.commit()
        db.refresh(task)

        return True, "添加成功", {"task_id": task.task_id, "task_name": task.task_name}
        



def tool_delete(cmd: str) -> tuple[bool, str, Any]:
    """解析 ``delete <id>``，按 ``task_id`` 删除并持久化。"""
    task_id_str = adjust_command(cmd)
    if not task_id_str:
        return False, "未输入任务id", None

    try:
        task_id = int(task_id_str)
    except ValueError:
        return False, "任务id必须是数字", None

    with SessionLocal() as db:
        task = db.get(TaskModel, task_id)
        if task is None:
            return False, "未找到任务", None
        db.delete(task)
        db.commit()
        return True, "删除任务成功", None



def tool_echo(cmd: str) -> tuple[bool, str, Any]:
    """回显 ``echo`` 后面的内容；data 为要显示的字符串。"""
    echo_content = adjust_command(cmd)
    if not echo_content:
        return False, "未输入回显内容", None
    return True, "ok", echo_content


def tool_time(cmd: str) -> tuple[bool, str, Any]:
    """返回当前时间的格式化字符串。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return True, "ok", now


def tool_help(cmd: str) -> tuple[bool, str, Any]:
    """返回 ``HELP_MESSAGE`` 字典，由命令行按 dict 分支打印键值。"""
    return True, "ok", HELP_MESSAGE


def tool_version(cmd: str) -> tuple[bool, str, Any]:
    """返回版本号字符串（来自 ``SYSTEM_MESSAGE``）。"""
    return True, "ok", SYSTEM_MESSAGE["version"]


# 列表顺序即匹配优先级：排在前面的 Tool 会先被尝试；若两条规则可能同时命中，顺序决定结果
TOOLS: list[Tool] = [
    Tool("list", match_list, tool_list),
    Tool("add", match_add, tool_add),
    Tool("delete", match_delete, tool_delete),
    Tool("echo", match_echo, tool_echo),
    Tool("time", match_time, tool_time),
    Tool("help", match_help, tool_help),
    Tool("version", match_version, tool_version),
]

AGENT = Agent(tools=TOOLS)


def run_tool(command: str) -> tuple[bool, str, Any]:
    """API 与命令行共用的统一入口。

    内部委托给全局 ``AGENT.run_text``，保证路由规则只有一份。

    Returns:
        ``(ok, msg, data)``：失败时 ``ok`` 为 False，``msg`` 为错误说明；成功时 ``data`` 依工具而异
        （list 为列表、help 为 dict、echo 为字符串等）。
    """
    return AGENT.run_text(command)


# ---------------------------------------------------------------------------
# 命令行：系统消息与主循环
# ---------------------------------------------------------------------------


def show_message(key: str) -> None:
    """根据键从 ``SYSTEM_MESSAGE`` 取一句话并打印（欢迎、提示、再见等）。"""
    print(SYSTEM_MESSAGE[key])


def handle_quit(command: str) -> None:
    """打印告别语；``command`` 一般为 ``"quit"`` 以对应 ``SYSTEM_MESSAGE`` 键。"""
    show_message(command)


def handle_invalid(command: str) -> None:
    """打印非法输入提示；``command`` 一般为 ``"invalid_command"``。"""
    show_message(command)


def _print_tool_result(ok_flag: bool, msg: str, data: Any) -> None:
    """把 ``run_tool`` 的三元组转成命令行可见输出（API 不走此函数，自行组 JSON）。

    规则：
        - ``ok_flag`` 为 False：只打印 ``msg``；
        - 成功且 ``data`` 为 None：不额外打印（例如某些仅状态成功的场景）；
        - ``data`` 为 list：元素若是带 ``task_id`` / ``task_name`` 的字典则按行号打印任务，其它 dict 按键值打印；
        - ``data`` 为 dict：每行 ``键 - 值``（用于 help）；
        - 其它类型：``print(data)``。
    """
    if not ok_flag:
        print(msg)
        return
    if data is None:
        return
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and "task_id" in item and "task_name" in item:
                print(f"{item['task_id']}. {item['task_name']}")
            elif isinstance(item, dict):
                for key, val in item.items():
                    print(f"{key} - {val}")
            else:
                print(item)
    elif isinstance(data, dict):
        for key, val in data.items():
            print(f"{key} - {val}")
    else:
        print(data)


def handle_command(command: str) -> bool:
    """处理一条用户输入（命令行专用）。

    - ``quit``：打印再见语并返回 False，外层主循环应退出；
    - 以 ``/`` 开头：视为非法格式，提示后返回 True 继续循环；
    - 其它：交给 ``run_tool``，再用 ``_print_tool_result`` 打印。

    Returns:
        True 表示继续主循环；False 表示应退出。
    """
    if command == "quit":
        handle_quit("quit")
        return False
    if command.startswith("/"):
        handle_invalid("invalid_command")
        return True

    ok_flag, msg, data = run_tool(command)
    _print_tool_result(ok_flag, msg, data)
    return True
