from __future__ import annotations

from pydantic import BaseModel, Field


class PlanStepSchema(BaseModel):
    action: str = Field(description="navigate | extract | wait | click | fill")
    target: str
    notes: str | None = None


class AgentPlanSchema(BaseModel):
    objective: str
    target_urls: list[str]
    steps: list[PlanStepSchema]
    expected_fields: list[str]
    stop_conditions: list[str]
    risk_notes: str | None = None
