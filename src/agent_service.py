"""Agent 工具服务模块（面向 API）。

职责概览：
    - 通过 ``Agent`` + ``Tool`` 将用户输入路由到具体工具（list/add/delete 等）；
    - 任务相关工具读写 PostgreSQL（``TaskModel`` + ``SessionLocal``）；
    - Step 执行记录同时写入内存短历史（``deque``）与数据库（``agent_steps``）；
    - ``run_tool`` 作为 API 统一入口，供 ``/agent/run`` 与 ``/agent/nl-run`` 调用。

约定：
    - 工具统一返回 ``(tool_succeeded: bool, msg: str, data: Any)``；
    - ``tool_succeeded`` 为 False 时由 API 返回失败消息；为 True 时由 API 包装 ``data`` 返回前端。
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy import select

from src.db.session import SessionLocal
from src.models.step import AgentStep
from src.models.task import TaskModel
from src.utils.datetime_fmt import format_step_ts_utc

logger = logging.getLogger(__name__)

# 各命令的说明文案，供 help 工具返回给前端展示
HELP_MESSAGE = {
    "help": "展示当前可输入的指令",
    "version": "展示当前版本信息",
    "echo": "回显后面的内容",
    "list": "展示当前任务列表",
    "add": "添加任务到任务列表",
    "delete": "删除任务列表中的任务",
    "time": "展示当前时间",
}

APP_VERSION = "1.0.0"


def adjust_command(command: str) -> str:
    """从整条命令里取出第一个词之后的文本。"""
    parts = command.split(" ")
    if len(parts) == 1:
        return ""
    return " ".join(parts[1:])


@dataclass
class Tool:
    """描述一个可调用工具（由 API 调用）。"""

    name: str
    match: Callable[[str], bool]
    run: Callable[[str], tuple[bool, str, Any]]


@dataclass
class Step:
    """单次工具调用的快照，用于日志与问题排查。"""

    tool_name: str
    input_text: str
    tool_succeeded: bool
    msg: str
    timestamp: str


def format_step(step: Step) -> str:
    return (
        f"调用{step.tool_name} 执行{step.input_text}，执行结果：{step.tool_succeeded}，"
        f"返回信息：{step.msg}；执行时间：{step.timestamp}"
    )


def _record_step(agent: "Agent", step: Step) -> None:
    # 先写内存快照（供同进程快速读），再写数据库（跨进程/重启可追溯）。
    agent.last_step = step
    agent.step_history.append(step)
    with SessionLocal() as db:
        try:
            agent_step = AgentStep(
                tool_name=step.tool_name,
                input_text=step.input_text,
                tool_succeeded=step.tool_succeeded,
                msg=step.msg,
            )
            db.add(agent_step)
            db.commit()
        except Exception:
            logger.exception("历史操作记录失败")
            db.rollback()


class Agent:
    """在用户输入上依次尝试工具 match，命中则执行 run。"""

    def __init__(self, tools: list[Tool]) -> None:
        self.tools = tools
        self.last_step: Step | None = None
        self.step_history: deque[Step] = deque(maxlen=50)

    def run_text(self, text: str) -> tuple[bool, str, Any]:
        """按注册顺序匹配工具，命中即执行并记录 step。"""
        text = text.strip()
        if not text:
            logger.info("未输入命令")
            return False, "请输入命令", None

        for tool in self.tools:
            step = Step(
                tool_name=tool.name,
                input_text=text,
                tool_succeeded=False,
                msg="",
                timestamp="",
            )
            if tool.match(text):
                tool_succeeded, msg, data = tool.run(text)
                step.tool_succeeded = tool_succeeded
                step.msg = msg
                step.timestamp = format_step_ts_utc(datetime.now(timezone.utc))
                _record_step(self, step)
                logger.info(format_step(step))
                return tool_succeeded, msg, data

        _record_step(
            self,
            Step(
                tool_name="unknown",
                input_text=text,
                tool_succeeded=False,
                msg="未知命令",
                timestamp=format_step_ts_utc(datetime.now(timezone.utc)),
            ),
        )
        logger.info("未知命令：%s", text)
        return False, "未知命令", None


def match_list(cmd: str) -> bool:
    return cmd == "list"


def match_add(cmd: str) -> bool:
    return cmd == "add" or cmd.startswith("add ")


def match_delete(cmd: str) -> bool:
    return cmd == "delete" or cmd.startswith("delete ")


def match_echo(cmd: str) -> bool:
    return cmd == "echo" or cmd.startswith("echo ")


def match_time(cmd: str) -> bool:
    return cmd == "time"


def match_help(cmd: str) -> bool:
    return cmd == "help"


def match_version(cmd: str) -> bool:
    return cmd == "version"


def tool_list(cmd: str) -> tuple[bool, str, Any]:
    with SessionLocal() as db:
        rows = (
            db.execute(select(TaskModel).order_by(TaskModel.task_id.asc()))
            .scalars()
            .all()
        )
        data = [{"task_id": r.task_id, "task_name": r.task_name} for r in rows]
        return True, "任务列表获取成功", data


def tool_add(cmd: str) -> tuple[bool, str, Any]:
    """新增任务，任务名判重，成功后返回 task_id 与 task_name。"""
    task_content = adjust_command(cmd)
    if not task_content:
        return False, "未输入任务内容", None

    with SessionLocal() as db:
        exists = db.execute(
            select(TaskModel).where(TaskModel.task_name == task_content)
        ).scalar_one_or_none()
        if exists:
            return False, "任务已存在", None

        task = TaskModel(task_name=task_content)
        db.add(task)
        db.commit()
        db.refresh(task)
        return True, "任务添加成功", {"task_id": task.task_id, "task_name": task.task_name}


def tool_delete(cmd: str) -> tuple[bool, str, Any]:
    """删除任务，要求参数是整数 task_id。"""
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
        return True, "任务删除成功", None


def tool_echo(cmd: str) -> tuple[bool, str, Any]:
    echo_content = adjust_command(cmd)
    if not echo_content:
        return False, "未输入回显内容", None
    return True, "回显内容获取成功", echo_content


def tool_time(cmd: str) -> tuple[bool, str, Any]:
    now = format_step_ts_utc(datetime.now(timezone.utc))
    return True, "当前时间获取成功", now


def tool_help(cmd: str) -> tuple[bool, str, Any]:
    return True, "帮助信息获取成功", HELP_MESSAGE


def tool_version(cmd: str) -> tuple[bool, str, Any]:
    return True, "版本信息获取成功", APP_VERSION


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


def run_tool(command: str) -> tuple[bool, str, dict | None]:
    """API 统一入口。"""
    return AGENT.run_text(command)
