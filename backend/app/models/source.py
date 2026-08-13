from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.session import Base
from backend.app.models.base import TimestampMixin, new_uuid


class Source(Base, TimestampMixin):
    # source registry (MASTER_SPEC section 28) - no browser action may target a
    # domain/URL not present here
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    domain: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    category: Mapped[str] = mapped_column(String, nullable=False)  # hotel_pricing | competitor_offer | campaign
    owner: Mapped[str] = mapped_column(String, nullable=False)
    access_type: Mapped[str] = mapped_column(String, default="public")  # public | partner | internal
    auth_required: Mapped[bool] = mapped_column(Boolean, default=False)
    review_required: Mapped[bool] = mapped_column(Boolean, default=False)
    health_state: Mapped[str] = mapped_column(String, default="HEALTHY")
    # HEALTHY | DEGRADED | UNSTABLE | FAILED | REVIEW_REQUIRED

    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    total_runs: Mapped[int] = mapped_column(Integer, default=0)
    total_failures: Mapped[int] = mapped_column(Integer, default=0)

    policies: Mapped[list["SourcePolicy"]] = relationship(back_populates="source", cascade="all, delete-orphan")


class SourcePolicy(Base, TimestampMixin):
    __tablename__ = "source_policies"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    source_id: Mapped[str] = mapped_column(String, ForeignKey("sources.id"), nullable=False)

    url_pattern: Mapped[str] = mapped_column(String, nullable=False)
    allowed_actions: Mapped[str] = mapped_column(String, default="navigate,extract,screenshot")
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, default=6)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=15)
    retry_cap: Mapped[int] = mapped_column(Integer, default=2)

    source: Mapped["Source"] = relationship(back_populates="policies")
