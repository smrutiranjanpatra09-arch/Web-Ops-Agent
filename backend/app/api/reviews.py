from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import require_role
from backend.app.database.session import get_db
from backend.app.models.review import Review
from backend.app.models.user import User
from backend.app.schemas.review import ReviewDecisionRequest, ReviewResponse
from backend.app.services.review_service import ReviewNotPendingError, decide_review

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


def _to_response(review: Review) -> ReviewResponse:
    return ReviewResponse(
        id=review.id, run_id=review.run_id, trigger_reason=review.trigger_reason, status=review.status,
        reviewer_id=review.reviewer_id, action=review.action, reason=review.reason,
        original_value=review.original_value, corrected_value=review.corrected_value,
        decided_at=review.decided_at, created_at=review.created_at.isoformat(),
    )


@router.get("", response_model=list[ReviewResponse])
def list_reviews(status: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Review)
    if status:
        query = query.filter(Review.status == status)
    reviews = query.order_by(Review.created_at.desc()).all()
    return [_to_response(r) for r in reviews]


@router.get("/{review_id}", response_model=ReviewResponse)
def get_review(review_id: str, db: Session = Depends(get_db)):
    review = db.get(Review, review_id)
    if review is None:
        raise HTTPException(404, f"Review '{review_id}' not found.")
    return _to_response(review)


@router.post("/{review_id}/decision", response_model=ReviewResponse)
def submit_decision(
    review_id: str,
    req: ReviewDecisionRequest,
    db: Session = Depends(get_db),
    reviewer: User = Depends(require_role("reviewer", "operations_owner", "administrator")),
):
    review = db.get(Review, review_id)
    if review is None:
        raise HTTPException(404, f"Review '{review_id}' not found.")
    try:
        review = decide_review(
            db, review, action=req.action, reviewer_id=reviewer.id,
            reason=req.reason, corrected_value=req.corrected_value,
        )
    except ReviewNotPendingError as exc:
        raise HTTPException(400, str(exc))
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return _to_response(review)
