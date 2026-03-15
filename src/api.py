from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

try:
    from src.schemas import TaskCreate, TaskDelete
except ModuleNotFoundError:
    from schemas import TaskCreate, TaskDelete

try:
    from src.commands import save_tasks, TASK_LIST
except ModuleNotFoundError:
    from commands import save_tasks, TASK_LIST

import logging

logger = logging.getLogger(__name__)

app = FastAPI(title="Agent Python Study Project", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# 健康监测。确保接口畅通
@app.get("/health")
def health():
    return {"status": "ok"}

# 添加任务接口
@app.post("/tasks")
def create_task(body: TaskCreate):
    try:
        description = body.description
        TASK_LIST.append(description)
        save_tasks()
        return {"id": len(TASK_LIST), "description": description}
    except Exception as e:
        logger.error("添加任务失败: %s", e)
        raise HTTPException(status_code=500, detail="添加任务失败")

# 
# 删除任务接口
# @app.delete("task/{task_id}")