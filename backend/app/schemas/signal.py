from __future__ import annotations

from pydantic import BaseModel


class SignalResponse(BaseModel):
    id: str
    run_id: str
    change_id: str | None
    signal_type: str
    severity: str
    observations: str
    business_impact: str | None
    confidence: float
    recommendation: str | None
    owner: str | None
    requires_human_review: bool
    created_at: str
