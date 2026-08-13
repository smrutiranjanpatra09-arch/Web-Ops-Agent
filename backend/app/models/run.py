from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.session import Base
from backend.app.models.base import TimestampMixin, new_uuid

# state machine per MASTER_SPEC section 5
RUN_STATES = (
    "CREATED", "VALIDATING", "PLANNING", "PLAN_READY", "AWAITING_APPROVAL", "APPROVED", "QUEUED",
    "BROWSER_STARTING", "BROWSING", "EXTRACTION", "VALIDATING_DATA", "SNAPSHOTTING", "COMPARING",
    "REASONING", "REVIEW_REQUIRED", "COMPLETING", "COMPLETED",
    "RECOVERY", "RERUN_REQUESTED", "FAILED", "CANCELLED",
)


class Run(Base, TimestampMixin):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    task_id: Mapped[str] = mapped_column(String, ForeignKey("tasks.id"), nullable=False)
    plan_id: Mapped[str] = mapped_column(String, ForeignKey("plans.id"), nullable=True)
    state: Mapped[str] = mapped_column(String, default="CREATED", nullable=False)
    schedule_id: Mapped[str] = mapped_column(String, ForeignKey("schedules.id"), nullable=True)
    error_type: Mapped[str] = mapped_column(String, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    retryable: Mapped[bool] = mapped_column(default=False)
    retry_count: Mapped[int] = mapped_column(default=0)

    # soft archival (engineering guidelines: never delete Postgres rows that break the
    # evidence chain) - archived runs are hidden from default list views but
    # remain fully queryable by ID with the whole evidence chain intact.
    archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    archived_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_by: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=True)

    steps: Mapped[list["RunStep"]] = relationship(back_populates="run", cascade="all, delete-orphan", order_by="RunStep.step_order")


class RunStep(Base, TimestampMixin):
    # transition log entry (MASTER_SPEC section 5: previous_state, new_state,
    # timestamp, run_id, reason, actor, metadata)
    __tablename__ = "run_steps"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("runs.id"), nullable=False)
    step_order: Mapped[int] = mapped_column(default=0)
    previous_state: Mapped[str] = mapped_column(String, nullable=True)
    new_state: Mapped[str] = mapped_column(String, nullable=False)
    reason: Mapped[str] = mapped_column(String, nullable=True)
    actor: Mapped[str] = mapped_column(String, default="system")  # system | service_worker | user:<id>
    step_metadata: Mapped[str] = mapped_column(Text, nullable=True)  # small JSON, IDs/refs only

    run: Mapped["Run"] = relationship(back_populates="steps")
