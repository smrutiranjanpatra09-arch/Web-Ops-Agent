from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.session import Base
from backend.app.models.base import TimestampMixin, new_uuid


class Review(Base, TimestampMixin):
    # human review (MASTER_SPEC section 15)
    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("runs.id"), nullable=False)
    trigger_reason: Mapped[str] = mapped_column(String, nullable=False)
    # low_confidence | sensitive_workflow | policy_warning | unfamiliar_source | ambiguous_recovery | major_source_change
    status: Mapped[str] = mapped_column(String, default="pending")  # pending | approved | rejected | corrected
    reviewer_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String, nullable=True)  # approve | reject | correct | rerun | request_schema_change
    reason: Mapped[str] = mapped_column(Text, nullable=True)
    original_value: Mapped[str] = mapped_column(String, nullable=True)
    corrected_value: Mapped[str] = mapped_column(String, nullable=True)
    decided_at: Mapped[str] = mapped_column(String, nullable=True)
