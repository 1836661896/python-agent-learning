"""Tasks 相关请求模型。"""

from pydantic import BaseModel, Field, field_validator


class TaskCreate(BaseModel):
    """创建任务请求体。"""

    description: str = Field(..., description="任务描述")

    @field_validator("description")
    @classmethod
    def description_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("任务描述不能为空")
        return v.strip()
