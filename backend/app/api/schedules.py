from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import require_role
from backend.app.database.session import get_db
from backend.app.models.schedule import Schedule
from backend.app.models.task import TaskTemplate
from backend.app.schemas.schedule import ScheduleCreateRequest, ScheduleResponse
from backend.app.services.schedule_service import trigger_schedule

router = APIRouter(prefix="/api/schedules", tags=["schedules"])
_ADMIN_ROLES = ("administrator", "operations_owner")

VALID_FREQUENCIES = {"one_time", "hourly", "daily", "weekly", "campaign_driven", "event_triggered"}


def _to_response(s: Schedule) -> ScheduleResponse:
    return ScheduleResponse(
        id=s.id, template_id=s.template_id, workflow_type=s.workflow_type, entity_key=s.entity_key,
        frequency=s.frequency, enabled=s.enabled, owner_team=s.owner_team,
        last_run_id=s.last_run_id, last_run_at=s.last_run_at, created_at=s.created_at.isoformat(),
    )


@router.post("", response_model=ScheduleResponse)
def create_schedule(req: ScheduleCreateRequest, db: Session = Depends(get_db), _=Depends(require_role(*_ADMIN_ROLES))):
    if req.frequency not in VALID_FREQUENCIES:
        raise HTTPException(400, f"Unknown frequency '{req.frequency}'. Choose from: {sorted(VALID_FREQUENCIES)}")
    template = db.get(TaskTemplate, req.template_id)
    if template is None:
        raise HTTPException(404, f"Template '{req.template_id}' not found.")

    schedule = Schedule(
        template_id=req.template_id, workflow_type=req.workflow_type, entity_key=req.entity_key,
        frequency=req.frequency, enabled=req.enabled, owner_team=req.owner_team,
    )
    db.add(schedule)
    db.commit()
    return _to_response(schedule)


@router.get("", response_model=list[ScheduleResponse])
def list_schedules(db: Session = Depends(get_db)):
    return [_to_response(s) for s in db.query(Schedule).order_by(Schedule.created_at.desc()).all()]


@router.delete("/{schedule_id}")
def delete_schedule(schedule_id: str, db: Session = Depends(get_db), _=Depends(require_role(*_ADMIN_ROLES))):
    schedule = db.get(Schedule, schedule_id)
    if schedule is None:
        raise HTTPException(404, f"Schedule '{schedule_id}' not found.")
    try:
        db.delete(schedule)
        db.commit()
    except IntegrityError:
        # a schedule that has already triggered at least one real run can't
        # be hard-deleted - runs.schedule_id references it, and deleting
        # would either violate that FK (what actually happened here, as a
        # bare unhandled 500) or, if cascaded, orphan real run history from
        # its scheduling context, breaking the audit trail the engineering
        # guidelines (section 11) require. Disable instead - same practical effect (it stops
        # firing) without destroying history.
        db.rollback()
        schedule.enabled = False
        db.commit()
        return {
            "deleted": False, "disabled": schedule_id,
            "reason": "schedule has existing runs and cannot be deleted; disabled instead",
        }
    return {"deleted": schedule_id}


@router.post("/{schedule_id}/trigger", response_model=dict)
def trigger_now(schedule_id: str, db: Session = Depends(get_db)):
    # manual trigger, bypassing the frequency check - useful for testing a
    # schedule or forcing an off-cycle run
    schedule = db.get(Schedule, schedule_id)
    if schedule is None:
        raise HTTPException(404, f"Schedule '{schedule_id}' not found.")
    try:
        run_id = trigger_schedule(db, schedule)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"run_id": run_id}
