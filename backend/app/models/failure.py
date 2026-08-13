from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.session import Base
from backend.app.models.base import TimestampMixin, new_uuid

# MASTER_SPEC section 19 error taxonomy
ERROR_TYPES = (
    "SOURCE_UNAVAILABLE", "PAGE_CHANGED", "SELECTOR_NOT_FOUND", "TIMEOUT", "LOGIN_REQUIRED",
    "ACCESS_BLOCKED", "POPUP_BLOCKED", "EXTRACTION_FAILED", "VALIDATION_FAILED",
    "MODEL_OUTPUT_INVALID", "POLICY_RESTRICTED", "STORAGE_FAILED", "QUEUE_FAILED", "UNKNOWN",
)


class Failure(Base, TimestampMixin):
    __tablename__ = "failures"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("runs.id"), nullable=False)
    run_step_id: Mapped[str] = mapped_column(String, ForeignKey("run_steps.id"), nullable=True)

    error_type: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    retryable: Mapped[bool] = mapped_column(Boolean, default=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    recovery_state: Mapped[str] = mapped_column(String, default="none")
    # none | attempted | recovered | exhausted


class RecoveryAttempt(Base, TimestampMixin):
    # bounded self-healing record (MASTER_SPEC section 13)
    __tablename__ = "recovery_attempts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("runs.id"), nullable=False)
    failure_id: Mapped[str] = mapped_column(String, ForeignKey("failures.id"), nullable=False)

    original_strategy: Mapped[str] = mapped_column(String, nullable=True)
    recovery_strategy: Mapped[str] = mapped_column(String, nullable=True)
    candidate_selector: Mapped[str] = mapped_column(String, nullable=True)
    result: Mapped[str] = mapped_column(String, default="pending")  # pending | validated | rejected
    confidence: Mapped[float] = mapped_column(Float, nullable=True)
    evidence_id: Mapped[str] = mapped_column(String, ForeignKey("evidence.id"), nullable=True)
