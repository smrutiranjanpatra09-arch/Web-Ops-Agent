from __future__ import annotations

from pydantic import BaseModel


class ChangeResponse(BaseModel):
    id: str
    run_id: str
    entity_name: str
    entity_key: str
    change_type: str
    previous_value: str | None
    current_value: str | None
    abs_diff: float | None
    delta_pct: float | None
    significance: str
    business_relevant: bool
    is_noise: bool
    created_at: str
