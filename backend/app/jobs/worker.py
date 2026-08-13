from __future__ import annotations

from redis import Redis
from rq import Worker

from backend.app.core.config import get_settings
from backend.app.database.session import SessionLocal
from backend.app.jobs.queue import RUN_QUEUE_NAME
from backend.app.models.run import Run
from backend.app.services.run_service import transition
from logger import get_logger

log = get_logger("jobs.worker")


def process_run(run_id: str, resume_after_approval: bool = False) -> None:
    # entry point invoked by RQ inside the `worker` container. Hands off to
    # the LangGraph orchestrator, which owns every transition from here
    # (planning through completion) - this function itself only validates
    # that the run is in a state we're allowed to pick up.
    expected_states = ("APPROVED",) if resume_after_approval else ("VALIDATING", "QUEUED")
    db = SessionLocal()
    try:
        run = db.get(Run, run_id)
        if run is None:
            log.error(f"process_run: run {run_id} not found")
            return
        if run.state not in expected_states:
            log.warning(f"process_run: run {run_id} not pickupable (state={run.state}), skipping")
            return
    finally:
        db.close()

    from backend.app.services.orchestrator import run_workflow_graph

    run_workflow_graph(run_id, resume_after_approval=resume_after_approval)


def main() -> None:
    settings = get_settings()
    conn = Redis.from_url(settings.redis_url)
    worker = Worker([RUN_QUEUE_NAME], connection=conn)
    log.info(f"worker starting, listening on queue '{RUN_QUEUE_NAME}'")
    worker.work()


if __name__ == "__main__":
    main()
