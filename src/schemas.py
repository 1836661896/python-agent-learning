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


# 统一命令参数
class AgentRunRequest(BaseModel):
    text: str = Field(..., description="命令内容")

    @field_validator("text")
    @classmethod
    def text_verify(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("命令不能为空")

        return v.strip()