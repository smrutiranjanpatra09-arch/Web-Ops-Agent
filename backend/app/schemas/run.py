from __future__ import annotations

from pydantic import BaseModel, Field


class RunStartRequest(BaseModel):
    task_id: str
    require_approval: bool | None = None


class RunResponse(BaseModel):
    id: str
    task_id: str
    plan_id: str | None = None
    state: str
    created_at: str
    updated_at: str
    error_type: str | None = None
    error_message: str | None = None
    archived: bool = False
    archived_at: str | None = None
    archived_by: str | None = None


class RejectRequest(BaseModel):
    reason: str | None = None


class ArchiveRunResponse(BaseModel):
    id: str
    archived: bool
    archived_at: str
    archived_by: str


class BulkArchiveRequest(BaseModel):
    older_than_days: int = Field(gt=0)
    state: str = "COMPLETED"


class BulkArchiveResponse(BaseModel):
    archived_run_ids: list[str]
    count: int


class RunDeleteRequest(BaseModel):
    reason: str = Field(min_length=1)
