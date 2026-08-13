from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.models.review import Review
from logger import get_logger
from mcp.schemas import ToolResult

log = get_logger("mcp.review_tools")


def create_review(db: Session, *, run_id: str, trigger_reason: str) -> ToolResult:
    review = Review(run_id=run_id, trigger_reason=trigger_reason, status="pending")
    db.add(review)
    db.flush()
    log.info(f"run={run_id} tool=create_review review_id={review.id} reason={trigger_reason}")
    return ToolResult(success=True, data={"review_id": review.id})
