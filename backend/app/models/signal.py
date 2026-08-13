from sqlalchemy import Boolean, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.session import Base
from backend.app.models.base import TimestampMixin, new_uuid


class Signal(Base, TimestampMixin):
    # operational signal (MASTER_SPEC section 14) - observations stay
    # deterministic; AI may explain the narrative only
    __tablename__ = "signals"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("runs.id"), nullable=False)
    change_id: Mapped[str] = mapped_column(String, ForeignKey("changes.id"), nullable=True)

    signal_type: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, default="low")  # low | medium | high | critical
    observations: Mapped[str] = mapped_column(Text, nullable=False)  # deterministic facts, plain text/JSON
    business_impact: Mapped[str] = mapped_column(Text, nullable=True)  # AI-generated narrative
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    recommendation: Mapped[str] = mapped_column(Text, nullable=True)
    owner: Mapped[str] = mapped_column(String, nullable=True)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, default=False)
