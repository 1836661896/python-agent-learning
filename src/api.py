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

# 获取任务列表
@app.get("/tasks")
def get_task_list():
    return TASK_LIST if TASK_LIST else []

# 添加任务接口
@app.post("/tasks")
def create_task(body: TaskCreate):
    try:
        description = body.description
        if len(TASK_LIST):
            TASK_LIST.append(
                {
                    "task_id": TASK_LIST[-1]["task_id"] + 1,
                    "task_name": description
                }
            )
        else:
            TASK_LIST.append(
                {
                    "task_id": 1,
                    "task_name": description
                }
            )
        save_tasks()
        return TASK_LIST[-1]
    except Exception as e:
        logger.error("添加任务失败: %s", e)
        raise HTTPException(status_code=500, detail="添加任务失败")

# 删除任务接口
@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    if any(t["task_id"] == task_id for t in TASK_LIST):
        TASK_LIST[:] = [t for t in TASK_LIST if t["task_id"] != task_id]
        save_tasks()
        return "删除任务成功"
    else:
        return "没有找到任务"
    
