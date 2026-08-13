from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.app.models.audit import AuditEvent
from backend.app.models.run import Run, RunStep
from backend.app.models.task import Task, TaskSource
from backend.app.services.state_machine import assert_valid_transition


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_task(db: Session, *, objective: str, workflow_type: str, entity_key: str,
                target_url: str | None = None, source_id: str | None = None,
                template_id: str | None = None, owner: str | None = None,
                risk_level: str = "low", review_required: bool = False,
                completion_criteria: str | None = None) -> Task:
    task = Task(
        objective=objective, workflow_type=workflow_type, entity_key=entity_key,
        template_id=template_id, owner=owner, risk_level=risk_level,
        review_required=review_required, completion_criteria=completion_criteria,
    )
    db.add(task)
    db.flush()

    if target_url:
        db.add(TaskSource(task_id=task.id, source_id=source_id, target_url=target_url))

    _record_audit(db, task_id=task.id, run_id=None, actor="user", action="task.created", result="success")
    db.commit()
    return task


def create_run(db: Session, *, task_id: str, schedule_id: str | None = None) -> Run:
    run = Run(task_id=task_id, state="CREATED", schedule_id=schedule_id)
    db.add(run)
    db.flush()
    _record_step(db, run.id, None, "CREATED", actor="system", reason="run created")
    _record_audit(db, task_id=task_id, run_id=run.id, actor="system", action="run.created", result="success")
    db.commit()
    return run


def transition(db: Session, run: Run, target_state: str, *, actor: str = "system",
               reason: str | None = None, error_type: str | None = None,
               error_message: str | None = None) -> Run:
    assert_valid_transition(run.state, target_state)
    previous = run.state
    run.state = target_state
    if error_type is not None:
        run.error_type = error_type
        run.error_message = error_message
        run.retryable = error_type not in ("POLICY_RESTRICTED", "LOGIN_REQUIRED", "ACCESS_BLOCKED")
    db.add(run)
    _record_step(db, run.id, previous, target_state, actor=actor, reason=reason)
    _record_audit(
        db, task_id=run.task_id, run_id=run.id, actor=actor,
        action=f"run.transition.{target_state.lower()}",
        result="failure" if target_state == "FAILED" else "success",
        reason=reason,
    )
    db.commit()
    return run


def create_rerun(db: Session, original_run: Run, *, reason: str) -> Run:
    # "Workflow Audit and Rerun" - starts a brand new run for the same task
    # so the original run stays intact for audit (MASTER_SPEC section 5.3)
    new_run = create_run(db, task_id=original_run.task_id)
    new_run = transition(db, new_run, "VALIDATING", reason=reason)
    return new_run


def _record_step(db: Session, run_id: str, previous_state: str | None, new_state: str, *,
                  actor: str, reason: str | None = None, step_order: int = 0) -> RunStep:
    existing_count = db.query(RunStep).filter(RunStep.run_id == run_id).count()
    step = RunStep(
        run_id=run_id, step_order=existing_count, previous_state=previous_state,
        new_state=new_state, actor=actor, reason=reason,
    )
    db.add(step)
    return step


def _record_audit(db: Session, *, task_id: str | None, run_id: str | None, actor: str,
                   action: str, result: str, reason: str | None = None) -> AuditEvent:
    event = AuditEvent(task_id=task_id, run_id=run_id, actor=actor, action=action, result=result, reason=reason)
    db.add(event)
    return event
