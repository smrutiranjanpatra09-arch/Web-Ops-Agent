from functools import lru_cache

from redis import Redis
from rq import Queue

from backend.app.core.config import get_settings

RUN_QUEUE_NAME = "runs"


@lru_cache
def get_redis() -> Redis:
    return Redis.from_url(get_settings().redis_url)


@lru_cache
def get_run_queue() -> Queue:
    return Queue(RUN_QUEUE_NAME, connection=get_redis())


def enqueue_run(run_id: str, resume_after_approval: bool = False) -> str:
    # persistence already happened by the time this is called (Task/Run rows
    # are committed) - this just hands the run_id to a worker. Job metadata
    # itself (job_id, status, retry_count) lives on RQ's own Redis-backed job
    # object plus the Run row in Postgres, per MASTER_SPEC section 29.
    job = get_run_queue().enqueue(
        "backend.app.jobs.worker.process_run", run_id, resume_after_approval, job_timeout=600,
    )
    return job.id
