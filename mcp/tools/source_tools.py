from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.models.source import Source
from mcp.schemas import ToolResult


def check_source_health(db: Session, domain: str) -> ToolResult:
    source = db.query(Source).filter(Source.domain == domain).one_or_none()
    if source is None:
        return ToolResult(success=False, error_type="POLICY_RESTRICTED", message=f"Source '{domain}' not registered")
    return ToolResult(success=True, data={
        "health_state": source.health_state,
        "consecutive_failures": source.consecutive_failures,
        "total_runs": source.total_runs,
        "total_failures": source.total_failures,
    })
