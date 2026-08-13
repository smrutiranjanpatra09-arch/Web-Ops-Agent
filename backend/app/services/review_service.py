from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.app.jobs.queue import enqueue_run
from backend.app.models.review import Review
from backend.app.models.run import Run
from backend.app.services.run_service import create_rerun, transition

VALID_ACTIONS = {"approve", "reject", "correct", "rerun", "request_schema_change"}


class ReviewNotPendingError(ValueError):
    pass


def decide_review(db: Session, review: Review, *, action: str, reviewer_id: str | None = None,
                  reason: str | None = None, corrected_value: str | None = None) -> Review:
    # reviewer feedback loop (MASTER_SPEC section 15) - never auto-modifies
    # production extraction logic; a corrected value here is a data
    # correction, not a change to extraction/validation code
    if action not in VALID_ACTIONS:
        raise ValueError(f"Unknown review action '{action}'. Choose from: {sorted(VALID_ACTIONS)}")
    if review.status != "pending":
        raise ReviewNotPendingError(f"Review '{review.id}' is not pending (status={review.status}).")

    status_by_action = {
        "approve": "approved", "reject": "rejected", "correct": "corrected",
        "rerun": "rejected", "request_schema_change": "rejected",
    }

    review.status = status_by_action[action]
    review.action = action
    review.reviewer_id = reviewer_id
    review.reason = reason
    if corrected_value is not None:
        review.corrected_value = corrected_value
    review.decided_at = datetime.now(timezone.utc).isoformat()
    db.add(review)

    run = db.get(Run, review.run_id)
    if action in ("approve", "correct"):
        transition(db, run, "COMPLETING", actor=f"user:{reviewer_id}" if reviewer_id else "user",
                   reason=f"review {action}d")
        transition(db, run, "COMPLETED", actor=f"user:{reviewer_id}" if reviewer_id else "user",
                   reason="run completed after review")
    elif action == "reject":
        transition(db, run, "FAILED", actor=f"user:{reviewer_id}" if reviewer_id else "user",
                   reason=reason or "rejected by reviewer",
                   error_type="POLICY_RESTRICTED", error_message=reason or "rejected by reviewer")
    elif action == "rerun":
        transition(db, run, "RERUN_REQUESTED", actor=f"user:{reviewer_id}" if reviewer_id else "user",
                   reason=reason or "reviewer requested rerun")
        db.flush()
        new_run = create_rerun(db, run, reason=f"rerun requested by reviewer for run {run.id}")
        db.commit()
        enqueue_run(new_run.id)
        return review
    elif action == "request_schema_change":
        transition(db, run, "FAILED", actor=f"user:{reviewer_id}" if reviewer_id else "user",
                   reason=reason or "schema change requested",
                   error_type="VALIDATION_FAILED", error_message=reason or "schema change requested")

    db.commit()
    return review
