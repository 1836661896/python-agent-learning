# WELCOME_MESSAGE = "欢迎来到 Python Agent 学习项目！"
# HINT_MESSAGE = "输入命令，输入 quit 退出。"
# HELP_MESSAGE = "当前支持的命令：\n - help：展示当前可输入的指令\n - quit：退出聊天\n 其他内容：直接展示"
from commands import show_message, handle_command, save_tasks
import logging

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logging.info("程序启动")
    show_message("welcome")
    show_message("hint")

    while True:
        try:
            command = input(">>> ")
            command = command.strip()

            should_continue = handle_command(command)

            if not should_continue:
                save_tasks()
                logging.info("用户退出，已保存任务")
                break
    
        except (KeyboardInterrupt, EOFError):
            print("\n确认要退出嘛？确定请输入y")
            try:
                command = input(">>> ")
                if command.strip().lower() == "y":
                    print("退出成功！")
                    save_tasks()
                    logging.info("用户确认退出，已保存任务")
                    break
            except (KeyboardInterrupt, EOFError):
                command = ""   # 再次 Ctrl+C 视为不退出，主循环继续

if __name__ == "__main__":
    main()