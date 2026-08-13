from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.session import Base
from backend.app.models.base import TimestampMixin, new_uuid


class RunSummary(Base, TimestampMixin):
    # AI-generated completion narrative (MASTER_SPEC section 14: the LLM may
    # explain the narrative, but the underlying observations stay deterministic
    # and live in changes/signals). One row per run that reaches REASONING.
    __tablename__ = "run_summaries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("runs.id"), nullable=False, unique=True)

    headline: Mapped[str] = mapped_column(Text, nullable=False)
    key_changes: Mapped[str] = mapped_column(Text, nullable=True)  # newline-delimited bullets
    recommended_owner: Mapped[str] = mapped_column(String, nullable=True)
    confidence_note: Mapped[str] = mapped_column(Text, nullable=True)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, default=False)
    generated_by: Mapped[str] = mapped_column(String, default="deterministic")  # gemini | ollama | deterministic
