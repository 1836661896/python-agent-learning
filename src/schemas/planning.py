from typing import Literal

from pydantic import BaseModel, Field, field_validator


class RoutingDecision(BaseModel):
    """本轮应走哪条业务线 (与 routing=auto 时的自动结果对齐)。"""

    route: Literal["chat", "mcp", "plan"]
    confidence: float | None = Field(default=None, ge=0, le=1)
    reason: str | None = None  # 可选：给调试或 UI 小字说明


class PlanStep(BaseModel):
    order: int = Field(..., ge=1, description="步骤序号，从 1 开始")
    description: str = Field(
        ..., min_length=1, description="这一步要做什么 / 问用户什么"
    )


class PlanOutline(BaseModel):
    """用户确认前：模型给出的步骤列表。"""

    title: str | None = None
    steps: list[PlanStep] = Field(default_factory=list)

    @field_validator("steps")
    @classmethod
    def steps_not_empty(cls, v: list[PlanStep]) -> list[PlanStep]:
        if not v:
            raise ValueError("steps 不能为空")
        return v
