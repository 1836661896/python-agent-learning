import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api_response import fail, ok
from src.db.deps import get_db
from src.models.task import TaskModel
from src.schemas import TaskCreate

logger = logging.getLogger(__name__)
router = APIRouter(tags=["tasks"])


@router.get("/tasks")
def get_task_list(db: Session = Depends(get_db)):
    """返回任务列表，按 task_id 升序，便于前端稳定渲染。"""
    rows = (
        db.execute(select(TaskModel).order_by(TaskModel.task_id.asc())).scalars().all()
    )
    data = [{"task_id": r.task_id, "task_name": r.task_name} for r in rows]
    return ok("请求成功", data)


@router.post("/tasks")
def create_task(body: TaskCreate, db: Session = Depends(get_db)):
    """创建任务；同名任务直接返回失败，避免重复数据。"""
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
    except Exception:
        logger.exception("添加任务失败")
        return fail("添加失败")


@router.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    """按主键删除任务，若不存在返回业务失败而非 404。"""
    task = db.get(TaskModel, task_id)
    if task is None:
        return fail("没有找到任务")

    db.delete(task)
    db.commit()
    return ok("删除任务成功")
