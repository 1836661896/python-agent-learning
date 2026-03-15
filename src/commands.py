from datetime import datetime
import json
import logging
logger = logging.getLogger(__name__)


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
        "add": "未输入任务内容"
    }
    command_list = command.split(" ")
    if len(command_list) == 1:
        print(error_list[command_list[0]])
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

# def delete_task(command: str) -> None:
#     task_id = adjust_command(command)
#     if task_id:
#         isIn = (t["task_id"] == task_id for t in TASK_LIST)
#         print(isIn)
        # if any(t["task_id"] == task_id for t in TASK_LIST):
            

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
    elif command.startswith("echo"):
        handle_echo(command)
        return True
    elif command.startswith("add"):
        add_task(command)
        return True
    elif command.startswith("delete"):
        delete_task(command)
    elif command.startswith("/"):
        handle_invalid("invalid_command")
        return True
    elif command in COMMAND_HANDLERS:
        COMMAND_HANDLERS[command](command)
        return True
    else:
        handle_message(command)
        return True