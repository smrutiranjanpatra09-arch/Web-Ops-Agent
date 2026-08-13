from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.app.jobs.queue import enqueue_run
from backend.app.models.schedule import Schedule
from backend.app.models.source import Source
from backend.app.models.task import TaskTemplate
from backend.app.services.run_service import create_run, create_task, transition
from logger import get_logger

log = get_logger("services.schedule")

FREQUENCY_INTERVAL_MINUTES = {
    "hourly": 60,
    "daily": 60 * 24,
    "weekly": 60 * 24 * 7,
}


def resolve_task_source(db: Session, template: TaskTemplate, entity_key: str) -> tuple[str, str | None]:
    # matches the template's workflow_type to an approved Source domain, then
    # fills in the path template with the entity - this is deliberately
    # simple (one source per workflow_type) since the source registry is
    # still small; a real deployment would need an explicit template<->source
    # mapping once there are multiple sources per workflow.
    source = db.query(Source).filter(Source.category == template.workflow_type).first()
    if source is None:
        raise ValueError(f"No approved Source found for workflow_type '{template.workflow_type}'")
    target_url = f"http://{source.domain}{template.path_template.format(entity=entity_key)}"
    return target_url, source.id


def trigger_schedule(db: Session, schedule: Schedule) -> str:
    # creates a real Task + Run from a Schedule's template, exactly the same
    # path a user hits via POST /api/tasks + POST /api/runs (MASTER_SPEC
    # section 19: scheduling produces real jobs, not a special code path)
    template = db.get(TaskTemplate, schedule.template_id)
    if template is None:
        raise ValueError(f"Schedule '{schedule.id}' references missing template '{schedule.template_id}'")

    target_url, source_id = resolve_task_source(db, template, schedule.entity_key)
    objective = template.objective_template.format(entity=schedule.entity_key)

    task = create_task(
        db, objective=objective, workflow_type=template.workflow_type, entity_key=schedule.entity_key,
        target_url=target_url, source_id=source_id, template_id=template.id,
        owner=schedule.owner_team, review_required=template.requires_approval,
    )
    run = create_run(db, task_id=task.id, schedule_id=schedule.id)
    run = transition(db, run, "VALIDATING", reason=f"triggered by schedule {schedule.id}")
    enqueue_run(run.id)

    schedule.last_run_id = run.id
    schedule.last_run_at = datetime.now(timezone.utc).isoformat()
    db.add(schedule)
    db.commit()

    log.info(f"schedule={schedule.id} triggered run={run.id} for entity={schedule.entity_key}")
    return run.id


def run_due_schedules(db: Session) -> list[str]:
    # called on a fixed tick by scheduler_service/main.py. "Due" is
    # determined by comparing now against last_run_at + the frequency's
    # interval - simple and deterministic, no external cron dependency.
    triggered = []
    schedules = db.query(Schedule).filter(Schedule.enabled == True).all()  # noqa: E712
    now = datetime.now(timezone.utc)

    for schedule in schedules:
        interval_minutes = FREQUENCY_INTERVAL_MINUTES.get(schedule.frequency)
        if interval_minutes is None:
            continue  # one_time/campaign_driven/event_triggered are not tick-driven

        if schedule.last_run_at is None:
            due = True
        else:
            last_run = datetime.fromisoformat(schedule.last_run_at)
            due = (now - last_run).total_seconds() >= interval_minutes * 60

        if due:
            try:
                run_id = trigger_schedule(db, schedule)
                triggered.append(run_id)
            except ValueError as exc:
                log.error(f"schedule={schedule.id} failed to trigger: {exc}")

    return triggered
