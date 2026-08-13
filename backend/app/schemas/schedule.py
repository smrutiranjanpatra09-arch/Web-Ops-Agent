from __future__ import annotations

from pydantic import BaseModel


class TaskTemplateCreateRequest(BaseModel):
    name: str
    workflow_type: str
    description: str | None = None
    path_template: str
    objective_template: str
    wait_selector: str
    expected_fields: list[str] = []
    default_frequency: str = "daily"
    owner_team: str | None = None
    requires_approval: bool = False
    stop_conditions: list[str] = []


class TaskTemplateResponse(BaseModel):
    id: str
    name: str
    workflow_type: str
    description: str | None
    path_template: str
    objective_template: str
    wait_selector: str
    default_frequency: str
    owner_team: str | None
    requires_approval: bool


class ScheduleCreateRequest(BaseModel):
    template_id: str
    workflow_type: str
    entity_key: str
    frequency: str  # one_time | hourly | daily | weekly | campaign_driven | event_triggered
    enabled: bool = True
    owner_team: str | None = None


class ScheduleResponse(BaseModel):
    id: str
    template_id: str
    workflow_type: str
    entity_key: str
    frequency: str
    enabled: bool
    owner_team: str | None
    last_run_id: str | None
    last_run_at: str | None
    created_at: str
