from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, TypedDict

from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

import time

from agents.completion import generate_summary
from agents.planner import build_plan
from backend.app.core.config import get_settings
from backend.app.database.session import SessionLocal
from backend.app.models.plan import Plan, PlanStep
from backend.app.models.run import Run
from backend.app.models.summary import RunSummary as RunSummaryRow
from backend.app.models.task import Task, TaskSource
from backend.app.services.run_service import transition
from browser.jobs import enqueue_browse, get_browser_queue
from extraction.schemas import ComparisonResult
from intelligence.source_health.recovery import attempt_selector_recovery, record_failure
from logger import RunContext
from mcp.schemas import ToolResult
from mcp.tools import comparison_tools, extract_tools, review_tools, signal_tools, snapshot_tools

BROWSE_POLL_TIMEOUT_SECONDS = 45
BROWSE_POLL_INTERVAL_SECONDS = 0.5

WORKFLOW_WAIT_SELECTORS = {
    "hotel_pricing_watch": ".hotel-card",
    "campaign_page_monitoring": ".campaign-hero",
    "competitor_offer_tracking": ".offer-card",
    "partner_update_review": ".update-item",
    "travel_trend_scanning": ".trend-item",
}

# the record field each workflow's record schema uses as its identifying
# name - matches the entity_name= values agents/reasoning_loop.py's compare_*
# functions already assign (hotel_name/slug/competitor/title/destination),
# so a Change row's entity_name can be joined back to the exact Snapshot rows
# it diffed.
WORKFLOW_ENTITY_NAME_FIELDS = {
    "hotel_pricing_watch": "hotel_name",
    "campaign_page_monitoring": "slug",
    "competitor_offer_tracking": "competitor",
    "partner_update_review": "title",
    "travel_trend_scanning": "destination",
}


def _record_entity_name(record: dict, workflow_type: str) -> str:
    field = WORKFLOW_ENTITY_NAME_FIELDS[workflow_type]
    return record[field]


class GraphState(TypedDict, total=False):
    run_id: str
    task_id: str
    workflow_type: str
    entity_key: str
    objective: str
    target_url: str
    source_id: Optional[str]
    resume_after_approval: bool
    _recovered_selector: Optional[str]
    evidence: dict
    records: list[dict]
    low_confidence_count: int
    changes: list[dict]
    current_snapshot_ids_by_entity_name: dict[str, str]
    error: Optional[str]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def plan_node(state: GraphState, db: Session) -> GraphState:
    log = RunContext(state["run_id"], "orchestrator.plan", task_id=state.get("task_id"))
    run = db.get(Run, state["run_id"])
    transition(db, run, "PLANNING", reason="generating browser plan")

    plan = build_plan(
        state["objective"], state["entity_key"], "", state["target_url"],
        workflow=state["workflow_type"], run_id=state["run_id"],
    )
    log.info(f"plan generated for {state['entity_key']}: {len(plan.steps)} step(s)")

    plan_row = Plan(
        task_id=state["task_id"],
        objective=plan.objective,
        status="ready",
        risk_notes=plan.risk_notes,
        stop_conditions="; ".join(plan.stop_conditions),
    )
    db.add(plan_row)
    db.flush()
    for order, step in enumerate(plan.steps):
        db.add(PlanStep(plan_id=plan_row.id, step_order=order, action=step.action, target=step.target, notes=step.notes))
    run.plan_id = plan_row.id

    transition(db, run, "PLAN_READY", reason="plan generated")
    db.commit()
    return {"run_id": state["run_id"]}


def approval_gate_node(state: GraphState, db: Session) -> GraphState:
    # sensitive tasks (task.review_required) stop here; approve_run() in
    # backend/app/api/runs.py resumes execution by re-enqueuing the run,
    # which re-enters this same graph and this node just passes through
    # once state has already moved past AWAITING_APPROVAL/APPROVED.
    log = RunContext(state["run_id"], "orchestrator.approval_gate", task_id=state.get("task_id"))
    run = db.get(Run, state["run_id"])
    task = db.get(Task, state["task_id"])

    if run.state == "PLAN_READY" and task.review_required:
        transition(db, run, "AWAITING_APPROVAL", reason="sensitive workflow requires approval")
        db.commit()
        log.info("run paused for human approval")
        return {"error": "__awaiting_approval__"}

    if run.state == "PLAN_READY":
        transition(db, run, "QUEUED", reason="auto-approved for browsing")
        transition(db, run, "BROWSER_STARTING", reason="starting browser execution")
    elif run.state == "APPROVED":
        transition(db, run, "QUEUED", reason="queued after approval")
        transition(db, run, "BROWSER_STARTING", reason="starting browser execution")
    db.commit()
    return {"run_id": state["run_id"]}


def browse_node(state: GraphState, db: Session) -> GraphState:
    # Playwright only runs inside the browser-worker container (engineering
    # guidelines, section 10: never inside the FastAPI/generic-worker process). This
    # dispatches the navigate step to the browser queue and polls the RQ job
    # result rather than calling browser_tools.navigate() in-process.
    if state.get("error") == "__awaiting_approval__":
        return {"run_id": state["run_id"]}
    log = RunContext(state["run_id"], "orchestrator.browse", task_id=state.get("task_id"))
    run = db.get(Run, state["run_id"])
    transition(db, run, "BROWSING", reason="dispatching to browser-worker")
    db.commit()

    wait_selector = state.get("_recovered_selector") or WORKFLOW_WAIT_SELECTORS[state["workflow_type"]]
    job_id = enqueue_browse(state["run_id"], state["target_url"], wait_selector)
    job = get_browser_queue().fetch_job(job_id)

    deadline = time.monotonic() + BROWSE_POLL_TIMEOUT_SECONDS
    while job.get_status() not in ("finished", "failed") and time.monotonic() < deadline:
        time.sleep(BROWSE_POLL_INTERVAL_SECONDS)
        job.refresh()

    if job.get_status() != "finished":
        message = f"browser-worker job {job_id} did not complete (status={job.get_status()})"
        log.warning(message)
        run = db.get(Run, state["run_id"])
        transition(db, run, "FAILED", reason=message, error_type="TIMEOUT", error_message=message)
        db.commit()
        return {"error": message}

    result = ToolResult(**job.result)
    if not result.success:
        log.warning(f"browse failed: {result.error_type}")
        run = db.get(Run, state["run_id"])
        failure = record_failure(
            db, run_id=state["run_id"], run_step_id=None, error_type=result.error_type or "UNKNOWN",
            message=result.message or "", retryable=result.error_type in ("SELECTOR_NOT_FOUND", "TIMEOUT"),
        )
        db.commit()

        if result.error_type == "SELECTOR_NOT_FOUND":
            transition(db, run, "RECOVERY", reason="selector not found, attempting self-healing")
            db.commit()
            recovered, candidate = attempt_selector_recovery(
                db, run_id=state["run_id"], failure=failure, workflow_type=state["workflow_type"],
                target_url=state["target_url"], original_selector=wait_selector,
            )
            db.commit()
            if recovered:
                log.info(f"recovered with candidate selector '{candidate}', retrying browse")
                transition(db, run, "QUEUED", reason="recovery succeeded, retrying browse")
                transition(db, run, "BROWSER_STARTING", reason="restarting browse after recovery")
                db.commit()
                return browse_node({**state, "_recovered_selector": candidate}, db)

        transition(db, run, "FAILED", reason=result.message, error_type=result.error_type, error_message=result.message)
        db.commit()
        return {"error": result.message}

    log.info(f"captured '{result.data['page_title']}' at {result.data['source_url']}")
    return {"evidence": result.data}


def extract_node(state: GraphState, db: Session) -> GraphState:
    if state.get("error"):
        return {"run_id": state["run_id"]}
    log = RunContext(state["run_id"], "orchestrator.extract", task_id=state.get("task_id"), evidence_id=state.get("evidence", {}).get("evidence_id"))
    run = db.get(Run, state["run_id"])
    transition(db, run, "EXTRACTION", reason="extracting structured records")

    evidence = state["evidence"]
    result = extract_tools.extract(
        state["workflow_type"], evidence["full_html"] or "", evidence["source_url"], state["entity_key"],
    )
    if not result.success:
        log.warning(f"extraction failed: {result.message}")
        transition(db, run, "FAILED", reason=result.message, error_type=result.error_type, error_message=result.message)
        db.commit()
        return {"error": result.message}

    transition(db, run, "VALIDATING_DATA", reason="validating extracted records")
    db.commit()
    log.info(f"extracted {len(result.data['records'])} record(s)")
    return {"records": result.data["records"], "low_confidence_count": result.data["low_confidence_count"]}


def snapshot_node(state: GraphState, db: Session) -> GraphState:
    if state.get("error"):
        return {"run_id": state["run_id"]}
    log = RunContext(state["run_id"], "orchestrator.snapshot", task_id=state.get("task_id"), evidence_id=state.get("evidence", {}).get("evidence_id"))
    run = db.get(Run, state["run_id"])
    transition(db, run, "SNAPSHOTTING", reason="persisting snapshot")

    # keyed by the record's own identifying name field (hotel_name,
    # campaign_slug, etc. - whichever key the workflow's record schema uses)
    # so compare_node can link each Change row back to the exact Snapshot
    # rows it diffed, not just to the run as a whole - required for the
    # evidence chain in the engineering guidelines (section 7) to be genuinely navigable.
    snapshot_ids_by_entity_name = {}
    for record in state["records"]:
        result = snapshot_tools.store_evidence_snapshot(
            db, run_id=state["run_id"], task_id=state["task_id"], source_id=state.get("source_id"),
            entity_key=state["entity_key"], workflow_type=state["workflow_type"],
            captured_at=state["evidence"]["captured_at"], record=record,
        )
        entity_name = _record_entity_name(record, state["workflow_type"])
        snapshot_ids_by_entity_name[entity_name] = result.data["snapshot_id"]

    db.commit()
    log.info(f"stored {len(snapshot_ids_by_entity_name)} snapshot(s)")
    return {"run_id": state["run_id"], "current_snapshot_ids_by_entity_name": snapshot_ids_by_entity_name}


def compare_node(state: GraphState, db: Session) -> GraphState:
    if state.get("error"):
        return {"run_id": state["run_id"]}
    log = RunContext(state["run_id"], "orchestrator.compare", task_id=state.get("task_id"))
    run = db.get(Run, state["run_id"])
    transition(db, run, "COMPARING", reason="comparing against prior snapshot")

    entity_name_field = WORKFLOW_ENTITY_NAME_FIELDS[state["workflow_type"]]
    prev_result = snapshot_tools.get_previous_snapshot(
        db, entity_key=state["entity_key"], workflow_type=state["workflow_type"], exclude_run_id=state["run_id"],
        entity_name_field=entity_name_field,
    )
    previous_records = prev_result.data["records"]

    result = comparison_tools.compare_snapshot(
        db, run_id=state["run_id"], workflow_type=state["workflow_type"],
        current_records=state["records"], previous_records=previous_records,
        current_snapshot_ids_by_entity_name=state.get("current_snapshot_ids_by_entity_name", {}),
        previous_snapshot_ids_by_entity_name=prev_result.data["snapshot_ids_by_entity_name"],
    )
    db.commit()
    relevant = [c for c in result.data["changes"] if c["business_relevant"]]
    log.info(f"{len(result.data['changes'])} comparison(s), {len(relevant)} business-relevant")
    return {"changes": result.data["changes"]}


def reason_node(state: GraphState, db: Session) -> GraphState:
    if state.get("error"):
        return {"run_id": state["run_id"]}
    log = RunContext(state["run_id"], "orchestrator.reason", task_id=state.get("task_id"))
    run = db.get(Run, state["run_id"])
    transition(db, run, "REASONING", reason="generating summary and signals")

    comparisons = [
        ComparisonResult(
            entity_name=c["entity_name"], entity_key=state["entity_key"], change_type=c["change_type"],
            previous_value=c["previous_value"], current_value=c["current_value"],
            abs_diff=c["abs_diff"], delta_pct=c["delta_pct"], business_relevant=c["business_relevant"],
        )
        for c in state["changes"]
    ]
    change_ids = [c["id"] for c in state["changes"] if c.get("id")]
    summary = generate_summary(
        state["run_id"], state["workflow_type"], state["entity_key"], comparisons, state.get("low_confidence_count", 0),
        change_ids=change_ids,
    )

    # persist the full narrative - reason_node previously used only .headline
    # and .recommended_owner and discarded key_changes/confidence_note, so the
    # UI had no way to show the actual AI insight
    db.add(RunSummaryRow(
        run_id=state["run_id"],
        headline=summary.headline,
        key_changes="\n".join(summary.key_changes),
        recommended_owner=summary.recommended_owner,
        confidence_note=summary.confidence_note,
        requires_human_review=summary.requires_human_review,
        generated_by=summary.generated_by,
    ))

    for c in state["changes"]:
        if not c["business_relevant"]:
            continue
        signal_tools.create_signal(
            db, run_id=state["run_id"], change_id=c["id"], signal_type=c["change_type"],
            severity="high" if c.get("significance") == "significant" else "medium",
            observations=f"{c['entity_name']}: {c['previous_value']} -> {c['current_value']}",
            business_impact=summary.headline, confidence=1.0 - (state.get("low_confidence_count", 0) * 0.1),
            recommendation=None, owner=summary.recommended_owner,
            requires_human_review=summary.requires_human_review,
        )

    if summary.requires_human_review:
        review_tools.create_review(db, run_id=state["run_id"], trigger_reason="low_confidence_or_significant_change")
        transition(db, run, "REVIEW_REQUIRED", reason="summary flagged for human review")
    else:
        transition(db, run, "COMPLETING", reason="no review required")
        transition(db, run, "COMPLETED", reason="run finished")

    db.commit()
    log.info(f"run finished: requires_review={summary.requires_human_review}")
    return {"run_id": state["run_id"]}


def build_graph(db: Session):
    graph = StateGraph(GraphState)
    graph.add_node("plan", lambda s: plan_node(s, db))
    graph.add_node("approval_gate", lambda s: approval_gate_node(s, db))
    graph.add_node("browse", lambda s: browse_node(s, db))
    graph.add_node("extract", lambda s: extract_node(s, db))
    graph.add_node("snapshot", lambda s: snapshot_node(s, db))
    graph.add_node("compare", lambda s: compare_node(s, db))
    graph.add_node("reason", lambda s: reason_node(s, db))

    graph.set_conditional_entry_point(
        lambda s: "approval_gate" if s.get("resume_after_approval") else "plan",
        {"plan": "plan", "approval_gate": "approval_gate"},
    )
    graph.add_edge("plan", "approval_gate")
    graph.add_edge("approval_gate", "browse")
    graph.add_edge("browse", "extract")
    graph.add_edge("extract", "snapshot")
    graph.add_edge("snapshot", "compare")
    graph.add_edge("compare", "reason")
    graph.add_edge("reason", END)
    return graph.compile()


def run_workflow_graph(run_id: str, resume_after_approval: bool = False) -> None:
    # entry point called by backend/app/jobs/worker.py. Orchestrates
    # plan->approval_gate->browse->extract->snapshot->compare->reason as a
    # real LangGraph StateGraph - this IS the orchestration layer
    # MASTER_SPEC section 12/14 requires, not a bare function chain.
    # resume_after_approval=True re-enters at approval_gate (skips re-planning)
    # for a run that was paused at AWAITING_APPROVAL and has just been approved.
    db = SessionLocal()
    try:
        run = db.get(Run, run_id)
        task = db.get(Task, run.task_id)
        task_source = db.query(TaskSource).filter(TaskSource.task_id == task.id).first()
        target_url = task_source.target_url if task_source else None
        if target_url is None:
            transition(db, run, "FAILED", reason="no target URL configured for task",
                       error_type="POLICY_RESTRICTED", error_message="Task has no associated source/target URL")
            db.commit()
            return

        graph = build_graph(db)
        graph.invoke({
            "run_id": run_id,
            "resume_after_approval": resume_after_approval,
            "task_id": task.id,
            "workflow_type": task.workflow_type,
            "entity_key": task.entity_key,
            "objective": task.objective,
            "target_url": target_url,
            "source_id": task_source.source_id if task_source else None,
        })
    finally:
        db.close()
