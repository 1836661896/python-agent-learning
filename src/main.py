# WELCOME_MESSAGE = "欢迎来到 Python Agent 学习项目！"
# HINT_MESSAGE = "输入命令，输入 quit 退出。"
# HELP_MESSAGE = "当前支持的命令：\n - help：展示当前可输入的指令\n - quit：退出聊天\n 其他内容：直接展示"
HELP_MESSAGE = {
    "help": "展示当前可输入的指令",
    "version": "展示当前版本信息",
    "quit": "退出",
    "echo": "回显后面的内容",
    "其他": "直接展示出来"
}

SYSTEM_MESSAGE = {
    "welcome": "欢迎来到 Python Agent 学习项目！",
    "hint": "输入命令，输入 quit 退出。",
    "quit": "再见！",
    "version": "1.0.0",
    "invalid_command": "未知命令格式，请直接输入文本或输入 help 查看帮助"
}

def show_message(command: str) -> None:
    print(SYSTEM_MESSAGE[command])

def handle_help(command: str) -> None:
    for name, desc in HELP_MESSAGE.items():
        print(f" - {name}：{desc}")

def handle_version(command: str) -> None:
    show_message(command)

def handle_invalid(command: str) -> None:
    show_message(command)

def handle_message(command: str) -> None:
    print(f"输入的内容为：{command}")

def handle_quit(command: str) -> None:
    show_message(command)

def handle_echo(command: str) -> None:
    parts = command.split(" ")
    if len(parts) == 1:
        print("")
    else:
        echo_message = " ".join(parts[1:])
        print(echo_message)


COMMAND_HANDLERS = {
    "help": handle_help,
    "version": handle_version,
    "echo": handle_echo
}


def handle_command(command: str) -> bool:
    """处理一条用户输入，返回是否继续循环"""
    if command == "quit":
        handle_quit("quit")
        return False
    elif command.startswith("echo"):
        handle_echo(command)
        return True
    elif command.startswith("/"):
        handle_invalid("invalid_command")
        return True
    elif command in COMMAND_HANDLERS:
        COMMAND_HANDLERS[command](command)
        return True
    else:
        handle_message(command)
        return True

def main():
    show_message("welcome")
    show_message("hint")

    while True:
        command = input(">>> ")

        should_continue = handle_command(command)

        if not should_continue:
            break


if __name__ == "__main__":
    main()