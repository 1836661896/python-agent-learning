from datetime import datetime
import json
import logging
logger = logging.getLogger(__name__)

from dataclasses import dataclass
from typing import Callable, Any


# 帮助展示的信息
HELP_MESSAGE = {
    "help": "展示当前可输入的指令",
    "version": "展示当前版本信息",
    "quit": "退出",
    "echo": "回显后面的内容",
    "list": "展示当前任务列表",
    "add": "添加任务到任务列表",
    "delete": "删除任务列表中的任务",
    "time": "展示当前时间",
    "其他": "直接展示出来"
}

# 系统目前支持的命令
SYSTEM_MESSAGE = {
    "welcome": "欢迎来到 Python Agent 学习项目！",
    "hint": "输入命令，输入 quit 退出。",
    "quit": "再见！",
    "version": "1.0.0",
    "invalid_command": "未知命令格式，请直接输入文本或输入 help 查看帮助"
}

# 统一处理系统消息，去除前方的指示词
def adjust_command(command: str) -> str:
    error_list = {
        "echo": "未输入回显内容",
        "add": "未输入任务内容",
        "delete": "未输入任务id"
    }
    command_list = command.split(" ")
    if len(command_list) == 1:
        try:
            print(error_list[command_list[0]])
        except ValueError:
            None
        return ""
    else:
        command_content = " ".join(command_list[1:])
        return command_content

TASK_FILE = "tasks.json"

# 任务列表
TASK_LIST = []

try:
    with open(TASK_FILE, "r", encoding="utf-8") as f:
        data = f.read()
        if data.strip():
            TASK_LIST = json.loads(data)

except FileNotFoundError:
    pass
except json.JSONDecodeError:
    pass

logger.info("已加载任务列表，共 %s 条", len(TASK_LIST))

# 展示任务列表
def handle_task(command: str) -> None:
    if len(TASK_LIST) == 0:
        print("暂无任务")
    else:
        for item in TASK_LIST:
            print(f"{item['task_id']}. {item['task_name']}")


def save_tasks() -> None:
    with open(TASK_FILE, "w", encoding="utf-8") as f:
        f.write(json.dumps(TASK_LIST, ensure_ascii=False, indent=2))

        logger.info("已保存任务列表，共 %s 条", len(TASK_LIST))


# 添加任务
def add_task(command: str) -> None:
    task_content = adjust_command(command)
    if task_content:
        if any(t["task_name"] == task_content for t in TASK_LIST):
            print("任务已添加，请不要重复添加")
        else:
            if len(TASK_LIST):
                task_id = TASK_LIST[-1]["task_id"] + 1
            else:
                task_id = 1
            TASK_LIST.append({
                "task_id": task_id,
                "task_name": task_content
            })
            save_tasks()
            logger.info("添加任务： %s", task_content)
            print("任务添加成功")

def delete_task(command: str) -> None:
    task_id_str = adjust_command(command)
    if task_id_str:
        try:
            task_id = int(task_id_str)
            if any(t["task_id"] == task_id for t in TASK_LIST):
                task_name = next((t["task_name"] for t in TASK_LIST if t["task_id"] == task_id), None)
                TASK_LIST[:] = [t for t in TASK_LIST if t["task_id"] != task_id]
                save_tasks()
                logger.info("删除任务：任务id %s，任务名称： %s", task_id, task_name )
                print("删除任务成功")
            else:
                print("没有找到任务")
        except ValueError:
            print("数据格式异常")

# 展示系统消息
def show_message(command: str) -> None:
    print(SYSTEM_MESSAGE[command])

# 展示目前系统消息对应的功能
def handle_help(command: str) -> None:
    for name, desc in HELP_MESSAGE.items():
        print(f" - {name}：{desc}")

# 展示版本
def handle_version(command: str) -> None:
    show_message(command)

# 报错信息
def handle_invalid(command: str) -> None:
    show_message(command)

# 展示用户输入的信息
def handle_message(command: str) -> None:
    print(f"输入的内容为：{command}")

# 展示当前时间
def handle_time(command: str) -> None:
    now = datetime.now()
    print(now.strftime("%Y-%m-%d %H:%M:%S"))

# 退出
def handle_quit(command: str) -> None:
    show_message(command)

# 回显用户输入的信息
def handle_echo(command: str) -> None:
    echo_message = adjust_command(command)
    if echo_message:
        print(echo_message)

# 快捷调用方法
COMMAND_HANDLERS = {
    "help": handle_help,
    "version": handle_version,
    "echo": handle_echo,
    "list": handle_task,
    "time": handle_time
}

# 处理输入的消息
def handle_command(command: str) -> bool:
    """处理一条用户输入，返回是否继续循环"""
    if command == "quit":
        handle_quit("quit")
        return False
    # elif command.startswith("echo"):
    #     handle_echo(command)
    #     return True
    # elif command.startswith("add"):
    #     add_task(command)
    #     return True
    # elif command.startswith("delete"):
    #     delete_task(command)
    #     return True
    elif command.startswith("/"):
        handle_invalid("invalid_command")
        return True

    else:
        ok_flag, msg, data = run_tool(command)
        if ok_flag:
            if data:
                if isinstance(data, list):
                    for t in data:
                        if isinstance(t, dict):
                            for key, item in t.items():
                                print(f"{key} - {item}")
                        else:
                            print(t)
                elif isinstance(data, dict):
                    for key, item in data.items():
                        print(f"{key} - {item}")
                else:
                    print(data)
        else:
            print(msg)
        return True
    # elif command in COMMAND_HANDLERS:
    #     COMMAND_HANDLERS[command](command)
    #     return True
    # else:
    #     handle_message(command)
    #     return True
    

"""------------------------------------------------------------------------"""

@dataclass
class Tool:
    name: str
    match: Callable[[str], bool]
    run: Callable[[str], tuple[bool, str, Any]]

class Agent:
    def __init__(self, tools: list[Tool]):
        self.tools = tools

    def run_text(self, text: str):
        text = text.strip()
        if not text:
            return False, "请输入命令", None
        
        for tool in self.tools:
            if tool.match(text):
                return tool.run(text)
        
        return False, "未知命令", None



def match_list(cmd: str) -> bool:
    return cmd == "list"

def match_add(cmd: str) -> bool:
    return cmd.startswith("add")

def match_delete(cmd: str) -> bool:
    return cmd.startswith("delete")

def match_echo(cmd: str) -> bool:
    return cmd.startswith("echo")

def match_time(cmd: str) -> bool:
    return cmd == "time"

def match_help(cmd: str) -> bool:
    return cmd == "help"

def match_version(cmd: str) -> bool:
    return cmd == "version"

def tool_list(cmd: str):
    return True, "ok", TASK_LIST

def tool_add(cmd: str):
    task_content = adjust_command(cmd)
    if not task_content:
        return False, "未输入任务内容", None
    
    if any(t["task_name"] == task_content for t in TASK_LIST):
        return False, "任务已存在", None
    
    task_id = TASK_LIST[-1]["task_id"] + 1 if TASK_LIST else 1
    task = {
        "task_id": task_id,
        "task_name": task_content
    }
    TASK_LIST.append(task)
    save_tasks()
    return True, "添加成功", task

def tool_delete(cmd: str):
    task_id_str = adjust_command(cmd)
    if not task_id_str:
        return False, "未输入任务id", None
    
    try:
        task_id = int(task_id_str)
    except ValueError:
        return False, "任务id必须是数字", None
    
    if any(t["task_id"] == task_id for t in TASK_LIST):
        TASK_LIST[:] = [t for t in TASK_LIST if t["task_id"] != task_id]
        save_tasks()
        return True, "删除任务成功", None
    else:
        return False, "未找到任务", None

def tool_echo(cmd: str):
    echo_content = adjust_command(cmd)
    if not echo_content:
        return False, "未输入回显内容", None
    return True, "ok", echo_content

def tool_time(cmd: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return True, "ok", now

def tool_help(cmd: str):
    return True, "ok", HELP_MESSAGE

def tool_version(cmd: str):
    return True, "ok", SYSTEM_MESSAGE["version"]



def run_tool(command: str):
    """
    给API/命令行的统一入口：
    返回（ok:bool, msg: str, data）
    """
    agent = Agent(
        tools=[
            Tool("list", match_list, tool_list),
            Tool("add", match_add, tool_add),
            Tool("delete", match_delete, tool_delete),
            Tool("echo", match_echo, tool_echo),
            Tool("time", match_time, tool_time),
            Tool("help", match_help, tool_help),
            Tool("version", match_version, tool_version),
        ]
    )
    return agent.run_text(command)