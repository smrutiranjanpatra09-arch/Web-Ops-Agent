from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.snapshot import Snapshot, SnapshotField

# HotelRecord/CampaignRecord/CompetitorOfferRecord all carry these two fields;
# everything else on the record becomes a SnapshotField row.
_COMMON_FIELDS = {"confidence", "validation_notes", "extracted_at", "source_url", "evidence_snippet"}


def create_snapshot(db: Session, *, run_id: str, task_id: str, source_id: str | None,
                     entity_key: str, workflow_type: str, captured_at: str,
                     record: dict, evidence_id: str | None = None) -> Snapshot:
    # one Snapshot per extracted record (one hotel, one campaign, one
    # competitor offer) - the fields dict becomes normalized SnapshotField rows
    # instead of a JSON blob, per the engineering guidelines, section 9 (no giant JSON for core entities)
    snapshot = Snapshot(
        run_id=run_id, task_id=task_id, source_id=source_id,
        entity_key=entity_key, workflow_type=workflow_type, captured_at=captured_at,
    )
    db.add(snapshot)
    db.flush()

    confidence = record.get("confidence", 1.0)
    validation_status = "valid" if confidence >= 0.7 else "warning"

    for field_name, value in record.items():
        if field_name in _COMMON_FIELDS or value is None:
            continue
        db.add(SnapshotField(
            snapshot_id=snapshot.id, evidence_id=evidence_id,
            field_name=field_name, raw_value=str(value), normalized_value=str(value),
            extraction_method="page_parser", confidence=confidence,
            validation_status=validation_status,
        ))
    db.flush()
    return snapshot


def get_snapshot_fields(db: Session, snapshot_id: str) -> dict[str, str]:
    rows = db.execute(select(SnapshotField).where(SnapshotField.snapshot_id == snapshot_id)).scalars().all()
    return {r.field_name: r.normalized_value for r in rows}


def get_latest_snapshot_before(db: Session, *, entity_key: str, workflow_type: str,
                               exclude_run_id: str) -> Snapshot | None:
    # most recent prior snapshot for this entity+workflow, used as the diff
    # baseline - excludes the current run so a run never compares against itself
    stmt = (
        select(Snapshot)
        .where(
            Snapshot.entity_key == entity_key,
            Snapshot.workflow_type == workflow_type,
            Snapshot.run_id != exclude_run_id,
        )
        .order_by(Snapshot.created_at.desc())
        .limit(1)
    )
    return db.execute(stmt).scalars().first()


def get_latest_snapshots_before(db: Session, *, entity_key: str, workflow_type: str,
                                exclude_run_id: str) -> list[Snapshot]:
    # a run may extract multiple records for one entity_key (e.g. 23 hotels
    # for city "Goa") - each becomes its own Snapshot row. The comparison
    # baseline must be every Snapshot row from the most recent prior RUN for
    # this entity+workflow, not a single arbitrary row, or per-record diffing
    # (matching by hotel_name/etc downstream) silently loses all but one record.
    latest = get_latest_snapshot_before(
        db, entity_key=entity_key, workflow_type=workflow_type, exclude_run_id=exclude_run_id,
    )
    if latest is None:
        return []
    stmt = (
        select(Snapshot)
        .where(Snapshot.run_id == latest.run_id, Snapshot.entity_key == entity_key,
               Snapshot.workflow_type == workflow_type)
    )
    return list(db.execute(stmt).scalars().all())
