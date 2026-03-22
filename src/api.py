from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from dataclasses import asdict

try:
    from src.schemas import TaskCreate, AgentRunRequest
except ModuleNotFoundError:
    from schemas import TaskCreate, AgentRunRequest

try:
    from src.commands import TASK_LIST, AGENT, save_tasks, run_tool
except ModuleNotFoundError:
    from commands import TASK_LIST, AGENT,  save_tasks, run_tool

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
    # exc.errors() 是一个列表，里面每一项是一个字段错误信息（dict）
    errors = exc.errors()

    # 先去第一个错误的msg
    # msg = "参数校验失败"
    # if errors:
    #     first = errors[0]
    #     if isinstance(first, dict) and isinstance(first.get("msg"), str):
    #         msg = first["msg"]
    #         if ", " in msg:
    #             msg = msg.split(", ", 1)[-1]

    msgs = []
    for err in errors:
        if isinstance(err, dict) and isinstance(err.get("msg"), str):
            m = err["msg"]
            if ", " in m:
                m = m.split(", ", 1)[-1]
            msgs.append(m)
        
        msg = "；".join(msgs) if msgs else "参数校验失败"
    
    return JSONResponse(
        status_code=200,
        content=fail(msg)
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
    
# 调用命令集
@app.post("/agent/run")
def use_tool(body: AgentRunRequest):
    text = body.text
    ok_flag, msg, data = run_tool(text)
    if ok_flag: 
        return ok(msg, data) 
    return fail(msg)

# 获取最后一步操作内容
@app.get("/agent/last-step")
def get_last_step():
    if AGENT.last_step is None:
        return fail("暂无执行记录")
    return ok("查询成功", AGENT.last_step)

# 获取操作历史记录
@app.get("/agent/steps")
def get_steps(limit: int = Query(20, ge=1, le=100)):
    raw = list(AGENT.step_history)
    if not raw:
        return ok("查询成功", [])
    recent = list(reversed(raw))[:limit]
    return ok("查询成功", [asdict(s) for s in recent])