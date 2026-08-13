from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.database.object_storage import delete_object
from backend.app.models.audit import AuditEvent
from backend.app.models.evidence import Evidence
from logger import get_logger

log = get_logger("services.retention")


def purge_expired_artifacts(db: Session) -> list[str]:
    # Real MinIO artifact retention (engineering guidelines, section 10 / product
    # spec section 10): only the raw binary in MinIO is ever deleted. The
    # Evidence row - URL, timestamp, selector, confidence, validation result -
    # is never removed, so the evidence chain stays intact and queryable;
    # only the object key is nulled out and artifact_purged flips to true.
    settings = get_settings()
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.retention_days_raw_artifacts)

    candidates = (
        db.query(Evidence)
        .filter(Evidence.artifact_purged.is_(False))
        .filter(Evidence.created_at < cutoff)
        .filter(
            (Evidence.screenshot_object_key.isnot(None)) | (Evidence.html_object_key.isnot(None))
        )
        .all()
    )

    purged_ids: list[str] = []
    for evidence in candidates:
        for object_key in (evidence.screenshot_object_key, evidence.html_object_key):
            if not object_key:
                continue
            try:
                delete_object(object_key)
            except Exception as exc:  # noqa: BLE001 - a missing/already-gone object must not block the sweep
                log.warning(f"evidence={evidence.id} failed to delete object '{object_key}': {exc}")

        evidence.screenshot_object_key = None
        evidence.html_object_key = None
        evidence.artifact_purged = True
        db.add(evidence)
        db.add(AuditEvent(
            task_id=None, run_id=evidence.run_id, actor="system",
            action="evidence.artifact_purged", result="success",
            reason=f"retention_days_raw_artifacts={settings.retention_days_raw_artifacts}",
        ))
        purged_ids.append(evidence.id)

    if purged_ids:
        db.commit()
        log.info(f"retention sweep purged {len(purged_ids)} artifact(s): {purged_ids}")

    return purged_ids
