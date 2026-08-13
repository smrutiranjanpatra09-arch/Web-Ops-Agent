from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.models.snapshot import Change, Snapshot
from backend.app.schemas.change import ChangeResponse

router = APIRouter(prefix="/api/changes", tags=["changes"])


def _to_response(c: Change) -> ChangeResponse:
    return ChangeResponse(
        id=c.id, run_id=c.run_id, entity_name=c.entity_name, entity_key=c.entity_key,
        change_type=c.change_type, previous_value=c.previous_value, current_value=c.current_value,
        abs_diff=c.abs_diff, delta_pct=c.delta_pct, significance=c.significance,
        business_relevant=c.business_relevant, is_noise=c.is_noise, created_at=c.created_at.isoformat(),
    )


@router.get("", response_model=list[ChangeResponse])
def list_changes(workflow_type: str | None = None, significance: str | None = None,
                 limit: int = 200, db: Session = Depends(get_db)):
    # journey-stage "Comparison" queue (Phase 32) - a live feed of recent
    # Change rows across every run, not just one. workflow_type is joined
    # through the current snapshot since Change itself doesn't carry it.
    query = db.query(Change)
    if workflow_type:
        query = query.join(Snapshot, Change.current_snapshot_id == Snapshot.id).filter(
            Snapshot.workflow_type == workflow_type,
        )
    if significance:
        query = query.filter(Change.significance == significance)
    changes = query.order_by(Change.created_at.desc()).limit(limit).all()
    return [_to_response(c) for c in changes]
