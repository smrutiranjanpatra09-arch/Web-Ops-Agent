from __future__ import annotations

from pydantic import BaseModel, Field


class TaskCreateRequest(BaseModel):
    objective: str
    workflow_type: str = Field(description="hotel_pricing_watch | competitor_offer_tracking | campaign_page_monitoring")
    entity_key: str
    target_url: str = Field(description="Full URL to browse, must match an approved Source domain")
    source_id: str | None = None
    template_id: str | None = None
    owner: str | None = None
    risk_level: str = "low"
    review_required: bool = False
    completion_criteria: str | None = None


class TaskResponse(BaseModel):
    id: str
    objective: str
    workflow_type: str
    entity_key: str
    owner: str | None
    risk_level: str
    review_required: bool
    created_at: str
