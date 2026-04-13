"""后端启动入口。

推荐开发命令：
    uvicorn src.api:app --reload

也支持：
    python -m src.main
"""

import uvicorn


def main() -> None:
    # 仅作为本地开发兜底入口；生产环境仍建议由进程管理器启动 uvicorn。
    uvicorn.run("src.api:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
