from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.models.source import Source
from backend.app.schemas.source import SourceResponse

router = APIRouter(prefix="/api/sources", tags=["sources"])


def _to_response(s: Source) -> SourceResponse:
    return SourceResponse(
        id=s.id, domain=s.domain, category=s.category, owner=s.owner, health_state=s.health_state,
        consecutive_failures=s.consecutive_failures, total_runs=s.total_runs, total_failures=s.total_failures,
    )


@router.get("", response_model=list[SourceResponse])
def list_sources(db: Session = Depends(get_db)):
    return [_to_response(s) for s in db.query(Source).order_by(Source.domain).all()]


@router.get("/{source_id}/health", response_model=SourceResponse)
def get_source_health(source_id: str, db: Session = Depends(get_db)):
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(404, f"Source '{source_id}' not found.")
    return _to_response(source)
