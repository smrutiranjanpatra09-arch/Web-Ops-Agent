from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.models.signal import Signal
from backend.app.models.snapshot import Change

# Deterministic keyword/entity match against real monitored data, no vector
# DB (spec explicitly defers pgvector/RAG as post-MVP optional). This is the
# only thing allowed to gate whether a chat reply is grounded in live
# observations vs. general LLM knowledge - never blend the two silently.
MATCH_LIMIT = 5


def find_relevant_context(db: Session, query: str) -> dict | None:
    terms = [w.strip().lower() for w in query.split() if len(w.strip()) >= 3]
    if not terms:
        return None

    matched_changes: list[Change] = []
    matched_signals: list[Signal] = []

    for term in terms:
        like = f"%{term}%"
        matched_changes.extend(
            db.query(Change)
            .filter(Change.business_relevant.is_(True))
            .filter(Change.entity_name.ilike(like) | Change.entity_key.ilike(like))
            .order_by(Change.created_at.desc())
            .limit(MATCH_LIMIT)
            .all()
        )
        matched_signals.extend(
            db.query(Signal)
            .filter(Signal.observations.ilike(like))
            .order_by(Signal.created_at.desc())
            .limit(MATCH_LIMIT)
            .all()
        )

    seen_change_ids: set[str] = set()
    changes = []
    for c in matched_changes:
        if c.id in seen_change_ids:
            continue
        seen_change_ids.add(c.id)
        changes.append(c)
    changes = changes[:MATCH_LIMIT]

    seen_signal_ids: set[str] = set()
    signals = []
    for s in matched_signals:
        if s.id in seen_signal_ids:
            continue
        seen_signal_ids.add(s.id)
        signals.append(s)
    signals = signals[:MATCH_LIMIT]

    if not changes and not signals:
        return None

    return {
        "changes": [
            {
                "id": c.id,
                "entity_name": c.entity_name,
                "change_type": c.change_type,
                "previous_value": c.previous_value,
                "current_value": c.current_value,
                "delta_pct": c.delta_pct,
            }
            for c in changes
        ],
        "signals": [
            {
                "id": s.id,
                "severity": s.severity,
                "observations": s.observations,
                "recommendation": s.recommendation,
            }
            for s in signals
        ],
    }
