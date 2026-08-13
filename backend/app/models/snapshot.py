from sqlalchemy import Boolean, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.session import Base
from backend.app.models.base import TimestampMixin, new_uuid


class Snapshot(Base, TimestampMixin):
    # one per successful run: task, source, timestamp, extracted values,
    # evidence refs, confidence, validation (MASTER_SPEC section 10)
    __tablename__ = "snapshots"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("runs.id"), nullable=False)
    task_id: Mapped[str] = mapped_column(String, ForeignKey("tasks.id"), nullable=False)
    source_id: Mapped[str] = mapped_column(String, ForeignKey("sources.id"), nullable=True)
    entity_key: Mapped[str] = mapped_column(String, nullable=False)
    workflow_type: Mapped[str] = mapped_column(String, nullable=False)
    captured_at: Mapped[str] = mapped_column(String, nullable=False)

    fields: Mapped[list["SnapshotField"]] = relationship(back_populates="snapshot", cascade="all, delete-orphan")


class SnapshotField(Base):
    # extraction_fields / snapshot_fields: entity, field, value, normalized_value,
    # confidence, evidence_id, validation_status (MASTER_SPEC section 9)
    __tablename__ = "snapshot_fields"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    snapshot_id: Mapped[str] = mapped_column(String, ForeignKey("snapshots.id"), nullable=False)
    evidence_id: Mapped[str] = mapped_column(String, ForeignKey("evidence.id"), nullable=True)

    field_name: Mapped[str] = mapped_column(String, nullable=False)
    raw_value: Mapped[str] = mapped_column(String, nullable=True)
    normalized_value: Mapped[str] = mapped_column(String, nullable=True)
    extraction_method: Mapped[str] = mapped_column(String, default="selector")
    # selector | page_parser | html_parser | semantic | llm_fallback
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    validation_status: Mapped[str] = mapped_column(String, default="valid")  # valid | warning | invalid

    snapshot: Mapped["Snapshot"] = relationship(back_populates="fields")


class Change(Base, TimestampMixin):
    # deterministic comparison output (MASTER_SPEC section 11) - never LLM-computed
    __tablename__ = "changes"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("runs.id"), nullable=False)
    current_snapshot_id: Mapped[str] = mapped_column(String, ForeignKey("snapshots.id"), nullable=True)
    previous_snapshot_id: Mapped[str] = mapped_column(String, ForeignKey("snapshots.id"), nullable=True)

    entity_name: Mapped[str] = mapped_column(String, nullable=False)
    entity_key: Mapped[str] = mapped_column(String, nullable=False)
    change_type: Mapped[str] = mapped_column(String, nullable=False)
    previous_value: Mapped[str] = mapped_column(String, nullable=True)
    current_value: Mapped[str] = mapped_column(String, nullable=True)
    abs_diff: Mapped[float] = mapped_column(Float, nullable=True)
    delta_pct: Mapped[float] = mapped_column(Float, nullable=True)
    significance: Mapped[str] = mapped_column(String, default="insignificant")
    # insignificant | minor | notable | significant
    business_relevant: Mapped[bool] = mapped_column(Boolean, default=False)
    is_noise: Mapped[bool] = mapped_column(Boolean, default=False)
    noise_reason: Mapped[str] = mapped_column(String, nullable=True)
