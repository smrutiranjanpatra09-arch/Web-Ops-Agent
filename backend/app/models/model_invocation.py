from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.session import Base
from backend.app.models.base import TimestampMixin, new_uuid


class ModelInvocation(Base, TimestampMixin):
    # audit record for every LLM call, regardless of caller (planner/
    # completion/recovery/chat/extraction fallback) - Phase 29's fix for
    # "LLM usage isn't visible": one choke point (agents/llm.py::call_structured)
    # writes this automatically, so no future caller can add an invisible call.
    # Stores prompt_summary/input_ref_ids, never raw prompt text with scraped
    # HTML, per the engineering guidelines' token/PII discipline.
    __tablename__ = "model_invocations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("runs.id"), nullable=True)
    chat_session_id: Mapped[str] = mapped_column(String, ForeignKey("chat_sessions.id"), nullable=True)

    node: Mapped[str] = mapped_column(String, nullable=False)
    # planner | completion | recovery | chat | extraction_fallback
    provider: Mapped[str] = mapped_column(String, nullable=False)  # gemini | ollama
    model_name: Mapped[str] = mapped_column(String, nullable=False)
    purpose: Mapped[str] = mapped_column(String, nullable=False)

    prompt_summary: Mapped[str] = mapped_column(Text, nullable=True)
    input_ref_ids: Mapped[str] = mapped_column(Text, nullable=True)  # small JSON string, IDs/refs only
    output_summary: Mapped[str] = mapped_column(Text, nullable=True)

    tokens_prompt: Mapped[int] = mapped_column(Integer, nullable=True)
    tokens_completion: Mapped[int] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)

    fallback_triggered: Mapped[bool] = mapped_column(Boolean, default=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
