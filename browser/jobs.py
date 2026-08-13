from __future__ import annotations

from functools import lru_cache

from redis import Redis
from rq import Queue

from backend.app.core.config import get_settings

BROWSER_QUEUE_NAME = "browser"


@lru_cache
def get_redis() -> Redis:
    return Redis.from_url(get_settings().redis_url)


@lru_cache
def get_browser_queue() -> Queue:
    return Queue(BROWSER_QUEUE_NAME, connection=get_redis())


def browse_job(run_id: str, target_url: str, wait_selector: str) -> dict:
    # runs INSIDE the browser-worker container (Playwright is only installed
    # there). Returns a plain dict (not an Evidence ORM object) since RQ
    # results cross a process boundary back to the caller's queue.
    from backend.app.database.session import SessionLocal
    from backend.app.models.run import Run
    from mcp.tools import browser_tools

    db = SessionLocal()
    try:
        run = db.get(Run, run_id)
        result = browser_tools.navigate(db, run, target_url, wait_selector)
        db.commit()
        return result.model_dump()
    finally:
        db.close()


def enqueue_browse(run_id: str, target_url: str, wait_selector: str) -> str:
    job = get_browser_queue().enqueue("browser.jobs.browse_job", run_id, target_url, wait_selector, job_timeout=60)
    return job.id
