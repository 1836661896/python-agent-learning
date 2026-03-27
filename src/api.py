from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.deps import get_db

from src.models.task import TaskModel
from src.models.step import AgentStep

try:
    from src.schemas import TaskCreate, AgentRunRequest
except ModuleNotFoundError:
    from schemas import TaskCreate, AgentRunRequest

try:
    from src.commands import AGENT, run_tool
except ModuleNotFoundError:
    from commands import AGENT, run_tool

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
def get_task_list(db: Session = Depends(get_db)):
    rows = db.execute(select(TaskModel).order_by(TaskModel.task_id.asc())).scalars().all()
    data = [{"task_id": r.task_id, "task_name": r.task_name} for r in rows]
    return ok("请求成功", data)

# 添加任务接口
@app.post("/tasks")
def create_task(body: TaskCreate, db: Session = Depends(get_db)):
    try:
        description = body.description

        exists = db.execute(
            select(TaskModel).where(TaskModel.task_name == description)
        ).scalar_one_or_none()
        if exists:
            return fail("任务已存在")
        
        task = TaskModel(task_name=description)
        db.add(task)
        db.commit()
        db.refresh(task)

        return ok("添加成功", {"task_id": task.task_id, "task_name": task.task_name})
        
    except Exception as e:
        logger.info("添加任务失败 %s", e)
        return fail("添加失败")




# 删除任务接口
@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(TaskModel, task_id)
    if task is None:
        return fail("没有找到任务")
    
    db.delete(task)
    db.commit()
    return ok("删除任务成功")
    
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
def get_last_step(db: Session = Depends(get_db)):
    row = db.execute(
        select(AgentStep).order_by(AgentStep.step_id.desc()).limit(1)
    ).scalar_one_or_none()
    
    if row is None:
        return fail("暂无执行记录")
    
    data = {
        "tool_name": row.tool_name,
        "input_text": row.input_text,
        "ok_flag": row.ok_flag,
        "msg": row.msg,
        "timestamp": row.timestamp.strftime("%Y-%m-%d %H:%M:%S %Z"),
    }
    return ok("查询成功", data)




# 获取操作历史记录
@app.get("/agent/steps")
def get_steps(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    rows = db.execute(
        select(AgentStep).order_by(AgentStep.step_id.desc()).limit(limit)
    ).scalars().all()
    data = [{
        "tool_name": r.tool_name,
        "input_text": r.input_text,
        "ok_flag": r.ok_flag,
        "msg": r.msg,
        "timestamp": r.timestamp.strftime("%Y-%m-%d %H:%M:%S %Z"),
    } for r in rows]
    if not data:
        return fail("暂无操作历史", [])
    return ok("查询成功", data)