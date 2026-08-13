from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from agents.digest import generate_run_digest
from backend.app.auth.dependencies import get_current_user, require_role
from backend.app.database.session import get_db
from backend.app.jobs.queue import enqueue_run
from backend.app.models.audit import AuditEvent
from backend.app.models.evidence import Evidence
from backend.app.models.plan import Plan
from backend.app.models.review import Review
from backend.app.models.run import Run
from backend.app.models.signal import Signal
from backend.app.models.snapshot import Change, Snapshot, SnapshotField
from backend.app.models.summary import RunSummary
from backend.app.models.task import Task
from backend.app.models.user import User
from backend.app.schemas.run import (
    ArchiveRunResponse, BulkArchiveRequest, BulkArchiveResponse, RejectRequest, RunDeleteRequest,
    RunResponse, RunStartRequest,
)
from backend.app.services.report_service import RunNotFoundError, build_run_report
from backend.app.services.run_service import create_rerun, create_run, transition

router = APIRouter(prefix="/api/runs", tags=["runs"])


def _to_response(run: Run) -> RunResponse:
    return RunResponse(
        id=run.id, task_id=run.task_id, plan_id=run.plan_id, state=run.state,
        created_at=run.created_at.isoformat(), updated_at=run.updated_at.isoformat(),
        error_type=run.error_type, error_message=run.error_message,
        archived=run.archived,
        archived_at=run.archived_at.isoformat() if run.archived_at else None,
        archived_by=run.archived_by,
    )


def _archive_run(db: Session, run: Run, *, actor_id: str) -> Run:
    # shared by the single-run and bulk-archive endpoints so both paths go
    # through the exact same soft-archival + audit logic (engineering guidelines: never
    # delete rows that break the evidence chain; every significant action
    # gets an AuditEvent).
    run.archived = True
    run.archived_at = datetime.now(timezone.utc)
    run.archived_by = actor_id
    db.add(run)
    db.add(AuditEvent(
        task_id=run.task_id, run_id=run.id, actor=f"user:{actor_id}",
        action="run.archived", result="success", reason=None,
    ))
    db.commit()
    db.refresh(run)
    return run


@router.post("", response_model=RunResponse)
def start_run(req: RunStartRequest, db: Session = Depends(get_db)):
    # validate -> persist -> enqueue -> return. Never runs browser/AI work inline.
    task = db.get(Task, req.task_id)
    if task is None:
        raise HTTPException(404, f"Task '{req.task_id}' not found.")

    # deliberately does NOT call the planner here - that's an LLM call, and
    # API handlers never run long/AI jobs inline (engineering guidelines, section 9). This
    # only validates+persists+enqueues; the worker generates the plan (and
    # stops at AWAITING_APPROVAL if the task requires review) before ever
    # touching a browser.
    run = create_run(db, task_id=task.id)
    run = transition(db, run, "VALIDATING", reason="task validated")
    enqueue_run(run.id)
    return _to_response(run)


@router.post("/{run_id}/approve", response_model=RunResponse)
def approve_run(run_id: str, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if run is None:
        raise HTTPException(404, f"Run '{run_id}' not found.")
    if run.state != "AWAITING_APPROVAL":
        raise HTTPException(400, f"Run '{run_id}' is not awaiting approval (state={run.state}).")

    if run.plan_id:
        plan = db.get(Plan, run.plan_id)
        plan.status = "approved"

    run = transition(db, run, "APPROVED", actor="user", reason="reviewer approved plan")
    enqueue_run(run.id, resume_after_approval=True)
    return _to_response(run)


@router.post("/{run_id}/reject", response_model=RunResponse)
def reject_run(run_id: str, req: RejectRequest = RejectRequest(), db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if run is None:
        raise HTTPException(404, f"Run '{run_id}' not found.")
    if run.state != "AWAITING_APPROVAL":
        raise HTTPException(400, f"Run '{run_id}' is not awaiting approval (state={run.state}).")

    if run.plan_id:
        plan = db.get(Plan, run.plan_id)
        plan.status = "rejected"
        plan.rejection_reason = req.reason

    run = transition(db, run, "CANCELLED", actor="user", reason=req.reason or "plan rejected by reviewer")
    return _to_response(run)


@router.get("", response_model=list[RunResponse])
def list_runs(state: str | None = None, states: str | None = None, workflow_type: str | None = None,
              limit: int = 200, offset: int = 0, since: str | None = None,
              include_archived: bool = False, db: Session = Depends(get_db)):
    # `state` matches one state; `states` is comma-separated for a journey
    # queue that covers a group (e.g. "BROWSER_STARTING,BROWSING") - Phase 32
    # needs the latter since Browser Monitor spans two states.
    # `workflow_type` filters via the owning Task since Run itself doesn't
    # carry workflow_type. `since` is an ISO-8601 timestamp lower bound on
    # created_at. Archived runs are excluded by default (Phase 37.2) - pass
    # include_archived=true to see them (they remain individually fetchable
    # by ID regardless).
    query = db.query(Run)
    if state:
        query = query.filter(Run.state == state)
    elif states:
        query = query.filter(Run.state.in_([s.strip() for s in states.split(",") if s.strip()]))

    if workflow_type:
        query = query.join(Task, Task.id == Run.task_id).filter(Task.workflow_type == workflow_type)

    if since:
        try:
            since_dt = datetime.fromisoformat(since)
        except ValueError:
            raise HTTPException(400, f"Invalid 'since' timestamp: '{since}'. Expected ISO-8601.")
        query = query.filter(Run.created_at >= since_dt)

    if not include_archived:
        query = query.filter(Run.archived.is_(False))

    runs = query.order_by(Run.created_at.desc()).offset(offset).limit(limit).all()
    return [_to_response(r) for r in runs]


@router.get("/{run_id}", response_model=RunResponse)
def get_run(run_id: str, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if run is None:
        raise HTTPException(404, f"Run '{run_id}' not found.")
    return _to_response(run)


@router.get("/{run_id}/steps")
def get_run_steps(run_id: str, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if run is None:
        raise HTTPException(404, f"Run '{run_id}' not found.")
    return [
        {
            "step_order": s.step_order, "previous_state": s.previous_state, "new_state": s.new_state,
            "actor": s.actor, "reason": s.reason, "created_at": s.created_at.isoformat(),
        }
        for s in sorted(run.steps, key=lambda s: s.step_order)
    ]


@router.get("/{run_id}/evidence")
def get_run_evidence(run_id: str, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if run is None:
        raise HTTPException(404, f"Run '{run_id}' not found.")
    rows = db.query(Evidence).filter(Evidence.run_id == run_id).order_by(Evidence.created_at).all()
    return [
        {
            "id": e.id, "source_url": e.source_url, "page_title": e.page_title, "captured_at": e.captured_at,
            "screenshot_object_key": e.screenshot_object_key, "html_object_key": e.html_object_key,
            "screenshot_url": f"/api/evidence/{e.screenshot_object_key}" if e.screenshot_object_key else None,
            "confidence": e.confidence, "validation_status": e.validation_status,
            "artifact_purged": e.artifact_purged,
        }
        for e in rows
    ]


@router.get("/{run_id}/results")
def get_run_results(run_id: str, db: Session = Depends(get_db)):
    # aggregate view: snapshots (with fields), changes, signals, reviews for
    # one run - the "what did this run actually find" endpoint the frontend
    # needs (MASTER_SPEC section 17 GET /api/runs/{id}/results)
    run = db.get(Run, run_id)
    if run is None:
        raise HTTPException(404, f"Run '{run_id}' not found.")

    snapshots = db.query(Snapshot).filter(Snapshot.run_id == run_id).all()
    snapshot_data = []
    for s in snapshots:
        fields = db.query(SnapshotField).filter(SnapshotField.snapshot_id == s.id).all()
        snapshot_data.append({
            "id": s.id, "entity_key": s.entity_key, "captured_at": s.captured_at,
            "fields": {f.field_name: f.normalized_value for f in fields},
        })

    changes = db.query(Change).filter(Change.run_id == run_id).all()
    signals = db.query(Signal).filter(Signal.run_id == run_id).all()
    reviews = db.query(Review).filter(Review.run_id == run_id).all()
    summary = db.query(RunSummary).filter(RunSummary.run_id == run_id).one_or_none()

    return {
        "run": _to_response(run).model_dump(),
        "summary": {
            "headline": summary.headline,
            "key_changes": [line for line in (summary.key_changes or "").split("\n") if line],
            "recommended_owner": summary.recommended_owner,
            "confidence_note": summary.confidence_note,
            "requires_human_review": summary.requires_human_review,
            "generated_by": summary.generated_by,
        } if summary else None,
        "snapshots": snapshot_data,
        "changes": [
            {
                "entity_name": c.entity_name, "change_type": c.change_type, "previous_value": c.previous_value,
                "current_value": c.current_value, "abs_diff": c.abs_diff, "delta_pct": c.delta_pct,
                "significance": c.significance, "business_relevant": c.business_relevant, "is_noise": c.is_noise,
                "current_snapshot_id": c.current_snapshot_id, "previous_snapshot_id": c.previous_snapshot_id,
            }
            for c in changes
        ],
        "signals": [
            {
                "id": sig.id, "signal_type": sig.signal_type, "severity": sig.severity,
                "observations": sig.observations, "business_impact": sig.business_impact,
                "confidence": sig.confidence, "owner": sig.owner,
                "requires_human_review": sig.requires_human_review,
            }
            for sig in signals
        ],
        "reviews": [
            {"id": r.id, "trigger_reason": r.trigger_reason, "status": r.status, "action": r.action}
            for r in reviews
        ],
    }


@router.get("/{run_id}/digest")
def get_run_digest(run_id: str, db: Session = Depends(get_db)):
    # computed on demand from already-persisted changes/signals (Phase 30.3) -
    # nothing new is persisted; idempotent and cheap so no caching needed yet.
    run = db.get(Run, run_id)
    if run is None:
        raise HTTPException(404, f"Run '{run_id}' not found.")
    digest = generate_run_digest(db, run_id)
    return digest.model_dump()


@router.get("/{run_id}/report.pdf")
def get_run_report_pdf(
    run_id: str, db: Session = Depends(get_db), actor: User = Depends(get_current_user),
):
    # Phase 35: portable PDF audit artifact for one run - any authenticated
    # user who can view the run (same as the other GET /api/runs/{id}/* read
    # endpoints), not role-restricted. All rendering happens in
    # report_service.build_run_report, which only reads already-persisted/
    # already-computed rows - no new calculation happens here or in the PDF.
    try:
        pdf_bytes = build_run_report(db, run_id, generated_by_user=actor)
    except RunNotFoundError:
        raise HTTPException(404, f"Run '{run_id}' not found.")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="run-{run_id}-report.pdf"'},
    )


@router.post("/{run_id}/rerun", response_model=RunResponse)
def rerun(run_id: str, db: Session = Depends(get_db)):
    original = db.get(Run, run_id)
    if original is None:
        raise HTTPException(404, f"Run '{run_id}' not found.")

    new_run = create_rerun(db, original, reason=f"rerun of {run_id}")
    enqueue_run(new_run.id)
    return _to_response(new_run)


@router.post("/{run_id}/archive", response_model=ArchiveRunResponse)
def archive_run(
    run_id: str, db: Session = Depends(get_db),
    actor: User = Depends(require_role("operations_owner", "administrator")),
):
    # soft archival only (Phase 37.2/engineering guidelines): the row, its steps, evidence,
    # snapshots, changes and signals are untouched - this just flips a flag
    # and hides the run from default list views.
    run = db.get(Run, run_id)
    if run is None:
        raise HTTPException(404, f"Run '{run_id}' not found.")
    if run.archived:
        raise HTTPException(400, f"Run '{run_id}' is already archived.")

    run = _archive_run(db, run, actor_id=actor.id)
    return ArchiveRunResponse(
        id=run.id, archived=run.archived, archived_at=run.archived_at.isoformat(), archived_by=run.archived_by,
    )


@router.post("/archive-bulk", response_model=BulkArchiveResponse)
def archive_bulk(
    req: BulkArchiveRequest, db: Session = Depends(get_db),
    actor: User = Depends(require_role("administrator")),
):
    # "archive all runs older than X days with state=COMPLETED" - loops the
    # exact same per-run archive logic used by the single-run endpoint
    # (never a raw SQL UPDATE) so each archived run gets its own AuditEvent.
    cutoff = datetime.now(timezone.utc) - timedelta(days=req.older_than_days)
    candidates = (
        db.query(Run)
        .filter(Run.state == req.state)
        .filter(Run.archived.is_(False))
        .filter(Run.created_at < cutoff)
        .all()
    )

    archived_ids = [_archive_run(db, run, actor_id=actor.id).id for run in candidates]
    return BulkArchiveResponse(archived_run_ids=archived_ids, count=len(archived_ids))


@router.delete("/{run_id}")
def hard_delete_run(
    run_id: str, req: RunDeleteRequest, db: Session = Depends(get_db),
    actor: User = Depends(require_role("administrator")),
):
    # genuine dev/test-junk removal only (Phase 37.4) - administrator-only,
    # requires the run to already be archived (can't hard-delete a live audit
    # trail in one step), and the confirmation reason is written to an
    # AuditEvent BEFORE the row is removed so the deletion itself survives
    # even though the run doesn't.
    run = db.get(Run, run_id)
    if run is None:
        raise HTTPException(404, f"Run '{run_id}' not found.")
    if not run.archived:
        raise HTTPException(400, f"Run '{run_id}' must be archived before it can be hard-deleted.")

    # AuditEvent.run_id references this run too, so the audit record must be
    # written first, then have its run_id cleared before the run itself is
    # removed - that's how the deletion event survives the row it describes
    # (task_id/reason/actor/result stay, the dangling run_id link doesn't).
    audit = AuditEvent(
        task_id=run.task_id, run_id=run.id, actor=f"user:{actor.id}",
        action="run.hard_deleted", result="success", reason=req.reason,
    )
    db.add(audit)
    db.commit()

    try:
        audit.run_id = None
        db.add(audit)
        db.delete(run)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            409,
            f"Run '{run_id}' still has dependent evidence/steps/signals rows referencing it "
            "and cannot be hard-deleted while they exist. This is a genuine dev/test-junk-only "
            "operation - runs with real evidence chains should stay archived instead.",
        )
    return {"deleted": run_id}
