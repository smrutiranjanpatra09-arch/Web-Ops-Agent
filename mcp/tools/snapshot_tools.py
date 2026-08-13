from __future__ import annotations

from sqlalchemy.orm import Session

from intelligence.snapshots.service import (
    create_snapshot, get_latest_snapshots_before, get_snapshot_fields,
)
from logger import get_logger
from mcp.schemas import ToolResult

log = get_logger("mcp.snapshot_tools")


def store_evidence_snapshot(db: Session, *, run_id: str, task_id: str, source_id: str | None,
                            entity_key: str, workflow_type: str, captured_at: str,
                            record: dict, evidence_id: str | None = None) -> ToolResult:
    snapshot = create_snapshot(
        db, run_id=run_id, task_id=task_id, source_id=source_id, entity_key=entity_key,
        workflow_type=workflow_type, captured_at=captured_at, record=record, evidence_id=evidence_id,
    )
    log.info(f"run={run_id} tool=store_evidence_snapshot snapshot_id={snapshot.id} entity={entity_key}")
    return ToolResult(success=True, data={"snapshot_id": snapshot.id})


def get_previous_snapshot(db: Session, *, entity_key: str, workflow_type: str, exclude_run_id: str,
                          entity_name_field: str | None = None) -> ToolResult:
    # a run may have produced multiple Snapshot rows for this entity_key (one
    # per extracted record, e.g. one per hotel in a city) - the baseline for
    # comparison is every row from the most recent prior run, not just one,
    # or per-record diffing downstream loses all but one record as "new".
    snapshots = get_latest_snapshots_before(
        db, entity_key=entity_key, workflow_type=workflow_type, exclude_run_id=exclude_run_id,
    )
    if not snapshots:
        return ToolResult(success=True, data={"records": [], "snapshot_ids_by_entity_name": {}})

    records = []
    snapshot_ids_by_entity_name = {}
    for snapshot in snapshots:
        fields = get_snapshot_fields(db, snapshot.id)
        # backfill the record-level metadata fields that were deliberately kept
        # out of SnapshotField (they're not business values, so storing them
        # there would be noise) but that the workflow record schemas still
        # require to reconstruct a comparable Pydantic record from this snapshot
        fields.setdefault("source_url", "")
        fields.setdefault("evidence_snippet", "")
        fields.setdefault("confidence", "1.0")
        fields.setdefault("extracted_at", snapshot.captured_at)
        records.append(fields)
        if entity_name_field and entity_name_field in fields:
            snapshot_ids_by_entity_name[fields[entity_name_field]] = snapshot.id

    return ToolResult(success=True, data={
        "records": records, "snapshot_ids_by_entity_name": snapshot_ids_by_entity_name,
        "captured_at": snapshots[0].captured_at,
    })
