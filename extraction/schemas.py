# shared schemas - keeping these in one place so planner/extraction/comparison
# all agree on field names
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class JobState(str, Enum):
    PENDING_APPROVAL = "pending_approval"
    PLANNED = "planned"
    RUNNING = "running"
    EXTRACTING = "extracting"
    COMPARING = "comparing"
    REASONING = "reasoning"
    COMPLETED = "completed"
    FAILED = "failed"
    PENDING_REVIEW = "pending_review"


class BrowserStep(BaseModel):
    action: str = Field(description="e.g. navigate, extract, wait")
    target: str = Field(description="URL or CSS selector this step operates on")
    notes: Optional[str] = None


class AgentPlan(BaseModel):
    objective: str
    target_urls: list[str]
    steps: list[BrowserStep]
    expected_fields: list[str]
    stop_conditions: list[str]
    risk_notes: Optional[str] = None


class HotelRecord(BaseModel):
    source_url: str
    city: str
    hotel_name: str
    price: Optional[float] = None
    currency: Optional[str] = None
    available: bool
    promo: Optional[str] = None
    rating: Optional[float] = None
    evidence_snippet: str
    confidence: float = Field(ge=0.0, le=1.0)
    validation_notes: Optional[str] = None
    extracted_at: str


class CampaignRecord(BaseModel):
    source_url: str
    slug: str
    headline: str
    cta: Optional[str] = None
    valid_until: Optional[str] = None
    evidence_snippet: str
    confidence: float = Field(ge=0.0, le=1.0)
    validation_notes: Optional[str] = None
    extracted_at: str


class CompetitorOfferRecord(BaseModel):
    source_url: str
    competitor: str
    offer_title: str
    discount_pct: Optional[float] = None
    evidence_snippet: str
    confidence: float = Field(ge=0.0, le=1.0)
    validation_notes: Optional[str] = None
    extracted_at: str


class PartnerUpdateRecord(BaseModel):
    source_url: str
    partner_name: str
    title: str
    body: Optional[str] = None
    evidence_snippet: str
    confidence: float = Field(ge=0.0, le=1.0)
    validation_notes: Optional[str] = None
    extracted_at: str


class TrendSignalRecord(BaseModel):
    source_url: str
    destination: str
    signal_text: str
    direction: Optional[str] = None  # up | down
    evidence_snippet: str
    confidence: float = Field(ge=0.0, le=1.0)
    validation_notes: Optional[str] = None
    extracted_at: str


class ChangeType(str, Enum):
    NEW_LISTING = "new_listing"
    REMOVED_LISTING = "removed_listing"
    PRICE_INCREASE = "price_increase"
    PRICE_DECREASE = "price_decrease"
    AVAILABILITY_CHANGE = "availability_change"
    PROMO_CHANGE = "promo_change"
    COPY_CHANGE = "copy_change"
    DISCOUNT_INCREASE = "discount_increase"
    DISCOUNT_DECREASE = "discount_decrease"
    SIGNAL_DIRECTION_CHANGE = "signal_direction_change"
    NO_CHANGE = "no_change"


class ComparisonResult(BaseModel):
    # entity_name/entity_key are generic on purpose: entity_name is the
    # hotel/campaign slug/competitor name, entity_key groups records that
    # should be compared against each other (city for hotels, workflow-wide
    # for campaigns/competitors)
    entity_name: str
    entity_key: str
    change_type: ChangeType
    previous_value: Optional[str] = None
    current_value: Optional[str] = None
    abs_diff: Optional[float] = None
    delta_pct: Optional[float] = None
    business_relevant: bool


class RunSummary(BaseModel):
    # generated_by is set by agents/completion.py so the UI can label whether a
    # narrative came from a real LLM call or the deterministic fallback -
    # never present fallback text as if it were AI reasoning
    generated_by: str = "deterministic"
    run_id: str
    workflow: str
    generated_at: str
    headline: str
    key_changes: list[str]
    recommended_owner: str
    confidence_note: str
    requires_human_review: bool


class SignalNarrative(BaseModel):
    # richer per-signal narrative (Phase 30.1). historical_context is computed
    # deterministically first (intelligence/signals/context_builder.py) and
    # handed to the LLM as an already-known fact to phrase, never something it
    # calculates itself (engineering guidelines, section 6).
    generated_by: str = "deterministic"
    headline: str
    business_impact: str
    historical_context: str
    recommended_action: str
    suggested_owner: str
    confidence_rationale: str
    risk_note: Optional[str] = None


class ErrorCategory(str, Enum):
    # distinct failure classes so the dashboard can show *why* runs fail,
    # rather than lumping every problem into one opaque error string
    SOURCE_UNAVAILABLE = "source_unavailable"
    PAGE_STRUCTURE_CHANGED = "page_structure_changed"
    EXTRACTION_FAILED = "extraction_failed"
    MODEL_RESPONSE_INVALID = "model_response_invalid"
    BROWSER_BLOCKED = "browser_blocked"
    POLICY_RESTRICTION = "policy_restriction"
    UNKNOWN = "unknown"


class Frequency(str, Enum):
    ONE_TIME = "one_time"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    CAMPAIGN_DRIVEN = "campaign_driven"
    EVENT_TRIGGERED = "event_triggered"


class TaskTemplate(BaseModel):
    # a reusable workflow definition so the agent doesn't rebuild the same plan
    # shape from scratch on every recurring run
    template_id: str
    name: str
    workflow: str
    description: Optional[str] = None
    path_template: str
    objective_template: str
    wait_selector: str
    expected_fields: list[str] = Field(default_factory=list)
    default_entities: list[str] = Field(default_factory=list)
    default_frequency: Frequency = Frequency.DAILY
    owner_team: Optional[str] = None
    requires_approval: bool = False
    stop_conditions: list[str] = Field(default_factory=list)


class Schedule(BaseModel):
    schedule_id: str
    template_id: str
    workflow: str
    entity: str
    frequency: Frequency
    enabled: bool = True
    owner_team: Optional[str] = None
    last_run_id: Optional[str] = None
    last_run_at: Optional[str] = None
    created_at: str


class ExecutedStep(BaseModel):
    # what the browser actually did, recorded alongside the *planned* steps so
    # the two can be diffed during an audit
    action: str
    target: str
    status: str  # ok | failed | skipped
    detail: Optional[str] = None
    at: str
