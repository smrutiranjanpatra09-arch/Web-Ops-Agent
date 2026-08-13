from __future__ import annotations

from sqlalchemy.orm import Session

from agents.reasoning_loop import (
    compare_campaign_records, compare_competitor_records, compare_hotel_records,
    compare_partner_updates, compare_trend_signals,
)
from backend.app.models.snapshot import Change
from extraction.schemas import (
    CampaignRecord, CompetitorOfferRecord, HotelRecord, PartnerUpdateRecord, TrendSignalRecord,
)
from intelligence.significance.engine import classify_significance, is_noise

_COMPARE_FNS = {
    "hotel_pricing_watch": (compare_hotel_records, HotelRecord),
    "campaign_page_monitoring": (compare_campaign_records, CampaignRecord),
    "competitor_offer_tracking": (compare_competitor_records, CompetitorOfferRecord),
    "partner_update_review": (compare_partner_updates, PartnerUpdateRecord),
    "travel_trend_scanning": (compare_trend_signals, TrendSignalRecord),
}


def compare_and_persist(db: Session, *, run_id: str, workflow_type: str, current_records: list[dict],
                        previous_records: list[dict],
                        current_snapshot_ids_by_entity_name: dict[str, str] | None = None,
                        previous_snapshot_ids_by_entity_name: dict[str, str] | None = None) -> list[Change]:
    # runs the deterministic per-workflow diff (agents/reasoning_loop.py, kept
    # as-is per the audit's KEEP classification) then persists each result as
    # a Change row with significance/noise classification layered on top.
    # Each Change is looked up by entity_name (not just tagged with one
    # snapshot_id for the whole run) because a single run can produce many
    # Snapshot rows under one entity_key (e.g. 23 hotels under city "Goa") -
    # without this, current_snapshot_id/previous_snapshot_id on the Change
    # row were always NULL, breaking the evidence chain's Change->Snapshot
    # link even though the actual Snapshot rows existed.
    current_snapshot_ids_by_entity_name = current_snapshot_ids_by_entity_name or {}
    previous_snapshot_ids_by_entity_name = previous_snapshot_ids_by_entity_name or {}
    compare_fn, record_type = _COMPARE_FNS[workflow_type]
    current = [record_type(**r) for r in current_records]
    previous = [record_type(**r) for r in previous_records]
    results = compare_fn(current, previous)

    changes: list[Change] = []
    for result in results:
        noise, noise_reason = is_noise(result.change_type.value, result.previous_value, result.current_value)
        significance = classify_significance(result.delta_pct)

        change = Change(
            run_id=run_id,
            current_snapshot_id=current_snapshot_ids_by_entity_name.get(result.entity_name),
            previous_snapshot_id=previous_snapshot_ids_by_entity_name.get(result.entity_name),
            entity_name=result.entity_name,
            entity_key=result.entity_key,
            change_type=result.change_type.value,
            previous_value=result.previous_value,
            current_value=result.current_value,
            abs_diff=result.abs_diff,
            delta_pct=result.delta_pct,
            significance=significance,
            business_relevant=result.business_relevant and not noise,
            is_noise=noise,
            noise_reason=noise_reason,
        )
        db.add(change)
        changes.append(change)

    db.flush()
    return changes
