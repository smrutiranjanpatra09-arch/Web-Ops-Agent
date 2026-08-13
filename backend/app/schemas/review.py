from __future__ import annotations

from pydantic import BaseModel


class ReviewDecisionRequest(BaseModel):
    action: str  # approve | reject | correct | rerun | request_schema_change
    reason: str | None = None
    corrected_value: str | None = None


class ReviewResponse(BaseModel):
    id: str
    run_id: str
    trigger_reason: str
    status: str
    reviewer_id: str | None
    action: str | None
    reason: str | None
    original_value: str | None
    corrected_value: str | None
    decided_at: str | None
    created_at: str
