from __future__ import annotations

from sqlalchemy.orm import Session

from intelligence.comparison.service import compare_and_persist
from logger import get_logger
from mcp.schemas import ToolResult

log = get_logger("mcp.comparison_tools")


def compare_snapshot(db: Session, *, run_id: str, workflow_type: str, current_records: list[dict],
                     previous_records: list[dict],
                     current_snapshot_ids_by_entity_name: dict[str, str] | None = None,
                     previous_snapshot_ids_by_entity_name: dict[str, str] | None = None) -> ToolResult:
    changes = compare_and_persist(
        db, run_id=run_id, workflow_type=workflow_type, current_records=current_records,
        previous_records=previous_records,
        current_snapshot_ids_by_entity_name=current_snapshot_ids_by_entity_name,
        previous_snapshot_ids_by_entity_name=previous_snapshot_ids_by_entity_name,
    )
    relevant = [c for c in changes if c.business_relevant]
    log.info(f"run={run_id} tool=compare_snapshot {len(changes)} result(s), {len(relevant)} business-relevant")
    return ToolResult(success=True, data={
        "changes": [
            {
                "id": c.id, "entity_name": c.entity_name, "change_type": c.change_type,
                "previous_value": c.previous_value, "current_value": c.current_value,
                "abs_diff": c.abs_diff, "delta_pct": c.delta_pct, "significance": c.significance,
                "business_relevant": c.business_relevant, "is_noise": c.is_noise,
            }
            for c in changes
        ],
    })
