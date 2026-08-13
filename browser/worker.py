from __future__ import annotations

from redis import Redis
from rq import Worker

from backend.app.core.config import get_settings
from logger import get_logger

BROWSER_QUEUE_NAME = "browser"
log = get_logger("browser.worker")


def main() -> None:
    settings = get_settings()
    conn = Redis.from_url(settings.redis_url)
    worker = Worker([BROWSER_QUEUE_NAME], connection=conn)
    log.info(f"browser-worker starting, listening on queue '{BROWSER_QUEUE_NAME}'")
    worker.work()


if __name__ == "__main__":
    main()
