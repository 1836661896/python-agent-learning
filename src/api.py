from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

try:
    from src.schemas import TaskCreate
except ModuleNotFoundError:
    from schemas import TaskCreate

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

def ok(msg: str, data=None):
    return {
        "code": 0,
        "data": data,
        "msg": msg
    }

def fail(msg: str, data=None):
    return {
        "code": 1,
        "data": data,
        "msg": msg
    }


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request, exc: RequestValidationError):
    return JSONResponse(
        status_code=200,
        content=fail("参数校验失败")
    )

@app.exception_handler(HTTPException)
def http_exception_handler(request, exc: HTTPException):
    msg = exc.detail if isinstance(exc.detail, str) else "请求失败"
    return JSONResponse(
        status_code=exc.status_code,
        content=fail(msg)
    )

# 健康监测。确保接口畅通
@app.get("/health")
def health():
    return ok("服务器正常")

# 获取任务列表
@app.get("/tasks")
def get_task_list():
    return ok("请求成功", TASK_LIST if TASK_LIST else [])

# 添加任务接口
@app.post("/tasks")
def create_task(body: TaskCreate):
    try:
        description = body.description
        
        if len(TASK_LIST):
            if any(t["task_name"] == description for t in TASK_LIST):
                return fail("任务已存在")
            else:
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
        return ok("添加成功")
    except Exception as e:
        logger.error("添加任务失败: %s", e)
        return fail("添加失败")

# 删除任务接口
@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    if any(t["task_id"] == task_id for t in TASK_LIST):
        TASK_LIST[:] = [t for t in TASK_LIST if t["task_id"] != task_id]
        save_tasks()
        return ok("删除任务成功")
    else:
        return fail("没有找到任务")
    
