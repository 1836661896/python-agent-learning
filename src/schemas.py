from pydantic import BaseModel, Field, field_validator

# 新增接口 参数描述
class TaskCreate(BaseModel):
    description: str = Field(..., description="任务描述")

    @field_validator("description")
    @classmethod
    def description_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("任务描述不能为空")
        return v.strip() 

# 删除接口 参数描述
class TaskDelete(BaseModel):
    task_id: str = Field(..., description="任务id")

    @field_validator("task_id")
    @classmethod
    def task_id_not_empty(cls, v: str) -> str:
        if not v or v.strip():
            raise ValueError("任务id不能为空")
        return v.strip()