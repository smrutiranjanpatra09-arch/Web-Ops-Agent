from __future__ import annotations

from apscheduler.schedulers.blocking import BlockingScheduler

from backend.app.database.session import SessionLocal
from backend.app.services.retention_service import purge_expired_artifacts
from backend.app.services.schedule_service import run_due_schedules
from logger import get_logger

log = get_logger("scheduler_service")

TICK_INTERVAL_SECONDS = 60
RETENTION_INTERVAL_SECONDS = 60 * 60  # hourly is plenty for a day-granularity retention window


def tick() -> None:
    db = SessionLocal()
    try:
        triggered = run_due_schedules(db)
        if triggered:
            log.info(f"tick: triggered {len(triggered)} run(s): {triggered}")
    finally:
        db.close()


def retention_tick() -> None:
    db = SessionLocal()
    try:
        purge_expired_artifacts(db)
    finally:
        db.close()


def main() -> None:
    scheduler = BlockingScheduler()
    scheduler.add_job(tick, "interval", seconds=TICK_INTERVAL_SECONDS)
    scheduler.add_job(retention_tick, "interval", seconds=RETENTION_INTERVAL_SECONDS)
    log.info(f"scheduler starting, tick every {TICK_INTERVAL_SECONDS}s, retention sweep every {RETENTION_INTERVAL_SECONDS}s")
    scheduler.start()


if __name__ == "__main__":
    main()
