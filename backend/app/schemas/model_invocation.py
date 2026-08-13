from __future__ import annotations

from pydantic import BaseModel


class ModelInvocationResponse(BaseModel):
    id: str
    run_id: str | None
    chat_session_id: str | None
    node: str
    provider: str
    model_name: str
    purpose: str
    prompt_summary: str | None
    input_ref_ids: dict | None
    output_summary: str | None
    tokens_prompt: int | None
    tokens_completion: int | None
    latency_ms: int
    fallback_triggered: bool
    success: bool
    error_message: str | None
    created_at: str
