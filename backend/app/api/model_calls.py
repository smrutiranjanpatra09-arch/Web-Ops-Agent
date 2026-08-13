import json
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.models.model_invocation import ModelInvocation
from backend.app.schemas.model_invocation import ModelInvocationResponse

router = APIRouter(tags=["model-calls"])


def _to_response(inv: ModelInvocation) -> ModelInvocationResponse:
    return ModelInvocationResponse(
        id=inv.id, run_id=inv.run_id, chat_session_id=inv.chat_session_id, node=inv.node,
        provider=inv.provider, model_name=inv.model_name, purpose=inv.purpose,
        prompt_summary=inv.prompt_summary,
        input_ref_ids=json.loads(inv.input_ref_ids) if inv.input_ref_ids else None,
        output_summary=inv.output_summary, tokens_prompt=inv.tokens_prompt,
        tokens_completion=inv.tokens_completion, latency_ms=inv.latency_ms,
        fallback_triggered=inv.fallback_triggered, success=inv.success,
        error_message=inv.error_message, created_at=inv.created_at.isoformat(),
    )


@router.get("/api/model-calls", response_model=list[ModelInvocationResponse])
def list_model_calls(node: str | None = None, provider: str | None = None,
                     since: datetime | None = None, limit: int = 100, db: Session = Depends(get_db)):
    # `since` is typed as datetime, not str, so FastAPI parses and validates
    # the ISO timestamp before it ever reaches the query - comparing a raw
    # string against created_at's timestamptz column let Postgres reject the
    # whole request with a bare 500 (UndefinedFunction: no >= operator for
    # timestamptz vs varchar), which then also looked like a CORS failure in
    # the browser since CORS headers aren't attached to that error path.
    query = db.query(ModelInvocation)
    if node:
        query = query.filter(ModelInvocation.node == node)
    if provider:
        query = query.filter(ModelInvocation.provider == provider)
    if since:
        query = query.filter(ModelInvocation.created_at >= since)
    invocations = query.order_by(ModelInvocation.created_at.desc()).limit(limit).all()
    return [_to_response(i) for i in invocations]


@router.get("/api/runs/{run_id}/model-calls", response_model=list[ModelInvocationResponse])
def list_run_model_calls(run_id: str, db: Session = Depends(get_db)):
    invocations = (
        db.query(ModelInvocation)
        .filter(ModelInvocation.run_id == run_id)
        .order_by(ModelInvocation.created_at.asc())
        .all()
    )
    return [_to_response(i) for i in invocations]
