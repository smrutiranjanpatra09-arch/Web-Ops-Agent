from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.models.signal import Signal
from logger import get_logger
from mcp.schemas import ToolResult

log = get_logger("mcp.signal_tools")


def create_signal(db: Session, *, run_id: str, change_id: str | None, signal_type: str, severity: str,
                  observations: str, business_impact: str | None, confidence: float,
                  recommendation: str | None, owner: str | None, requires_human_review: bool) -> ToolResult:
    signal = Signal(
        run_id=run_id, change_id=change_id, signal_type=signal_type, severity=severity,
        observations=observations, business_impact=business_impact, confidence=confidence,
        recommendation=recommendation, owner=owner, requires_human_review=requires_human_review,
    )
    db.add(signal)
    db.flush()
    log.info(f"run={run_id} tool=create_signal signal_id={signal.id} type={signal_type} severity={severity}")
    return ToolResult(success=True, data={"signal_id": signal.id})
