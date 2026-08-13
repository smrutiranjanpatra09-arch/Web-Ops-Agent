from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.models.failure import Failure, RecoveryAttempt

router = APIRouter(prefix="/api/failures", tags=["failures"])


@router.get("")
def list_failures(db: Session = Depends(get_db)):
    rows = db.query(Failure).order_by(Failure.created_at.desc()).limit(200).all()
    result = []
    for f in rows:
        attempts = db.query(RecoveryAttempt).filter(RecoveryAttempt.failure_id == f.id).all()
        result.append({
            "id": f.id, "run_id": f.run_id, "error_type": f.error_type, "message": f.message,
            "retryable": f.retryable, "retry_count": f.retry_count, "recovery_state": f.recovery_state,
            "created_at": f.created_at.isoformat(),
            "recovery_attempts": [
                {
                    "candidate_selector": a.candidate_selector, "result": a.result,
                    "confidence": a.confidence, "recovery_strategy": a.recovery_strategy,
                }
                for a in attempts
            ],
        })
    return result
