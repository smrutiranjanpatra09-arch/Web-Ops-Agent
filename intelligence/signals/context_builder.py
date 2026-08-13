# deterministic prep step for signal narration (Phase 30.1 / engineering
# guidelines, section 6: the LLM never computes diffs/frequency - it only narrates facts this
# module has already computed in plain Python from real Postgres history).
from __future__ import annotations

from datetime import timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.snapshot import Change

# how many prior changes (for the same entity+field/change_type) to look at
# when building frequency/direction context - "last N changes", not the full
# history, so the prompt stays compact (engineering guidelines, section 5).
HISTORY_WINDOW = 10
MIN_HISTORY_FOR_CONTEXT = 5


def build_signal_context(db: Session, change: Change) -> dict:
    # queries the last HISTORY_WINDOW changes for this entity_key+entity_name
    # (same tracked entity) ordered most-recent-first, and computes frequency/
    # direction/streak in code. Returns a structured dict meant to be handed
    # to the LLM as already-computed fact, never as raw rows to reason over.
    history = list(db.execute(
        select(Change)
        .where(Change.entity_key == change.entity_key)
        .where(Change.entity_name == change.entity_name)
        .where(Change.id != change.id)
        .order_by(Change.created_at.desc())
        .limit(HISTORY_WINDOW)
    ).scalars())

    same_type = [h for h in history if h.change_type == change.change_type]
    occurrence_count = len(same_type) + 1  # +1 for the current change itself

    # direction streak: how many of the most-recent same-type changes (incl.
    # this one) moved the same way, using change_type as the direction signal
    # (e.g. price_increase vs price_decrease are distinct enums already)
    streak = 1
    for h in same_type:
        if h.change_type == change.change_type:
            streak += 1
        else:
            break

    window_days = None
    if history:
        oldest = min(h.created_at for h in history)
        newest = change.created_at or oldest
        if oldest and newest:
            # some DB drivers (e.g. sqlite, used in tests) return naive
            # datetimes even when the column is timezone-aware in Postgres -
            # normalize both sides before subtracting so this never raises.
            if oldest.tzinfo is None:
                oldest = oldest.replace(tzinfo=timezone.utc)
            if newest.tzinfo is None:
                newest = newest.replace(tzinfo=timezone.utc)
            window_days = max((newest - oldest).days, 0)

    has_enough_history = len(history) >= MIN_HISTORY_FOR_CONTEXT

    return {
        "entity_key": change.entity_key,
        "entity_name": change.entity_name,
        "change_type": change.change_type,
        "occurrence_count_same_type": occurrence_count,
        "direction_streak": streak,
        "history_window_size": len(history),
        "window_days": window_days,
        "has_sufficient_history": has_enough_history,
        "recent_history": [
            {
                "change_type": h.change_type,
                "previous_value": h.previous_value,
                "current_value": h.current_value,
                "delta_pct": h.delta_pct,
                "created_at": h.created_at.isoformat() if h.created_at else None,
            }
            for h in history
        ],
    }


def summarize_historical_context(context: dict) -> str:
    # deterministic, human-readable fallback sentence built purely from
    # build_signal_context()'s counts - used when no LLM is configured, and
    # also as the literal fact string handed into the LLM prompt so it has
    # nothing left to compute (engineering guidelines, section 6).
    count = context["occurrence_count_same_type"]
    entity = context["entity_name"]
    change_type = context["change_type"].replace("_", " ")

    if count <= 1:
        return f"First recorded {change_type} for {entity} in the observed history."

    ordinal = _ordinal(count)
    window = context.get("window_days")
    if window:
        return f"{ordinal} {change_type} for {entity} in the last {window} day(s)."
    return f"{ordinal} {change_type} for {entity} in recent history."


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"
