from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.models.signal import Signal
from backend.app.schemas.signal import SignalResponse

router = APIRouter(prefix="/api/signals", tags=["signals"])


def _to_response(signal: Signal) -> SignalResponse:
    return SignalResponse(
        id=signal.id, run_id=signal.run_id, change_id=signal.change_id, signal_type=signal.signal_type,
        severity=signal.severity, observations=signal.observations, business_impact=signal.business_impact,
        confidence=signal.confidence, recommendation=signal.recommendation, owner=signal.owner,
        requires_human_review=signal.requires_human_review, created_at=signal.created_at.isoformat(),
    )


@router.get("", response_model=list[SignalResponse])
def list_signals(severity: str | None = None, owner: str | None = None,
                 run_id: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Signal)
    if severity:
        query = query.filter(Signal.severity == severity)
    if owner:
        query = query.filter(Signal.owner == owner)
    if run_id:
        query = query.filter(Signal.run_id == run_id)
    signals = query.order_by(Signal.created_at.desc()).all()
    return [_to_response(s) for s in signals]


@router.get("/{signal_id}", response_model=SignalResponse)
def get_signal(signal_id: str, db: Session = Depends(get_db)):
    signal = db.get(Signal, signal_id)
    if signal is None:
        raise HTTPException(404, f"Signal '{signal_id}' not found.")
    return _to_response(signal)
