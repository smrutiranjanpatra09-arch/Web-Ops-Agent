from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.session import Base
from backend.app.models.base import TimestampMixin, new_uuid


class Evidence(Base, TimestampMixin):
    # metadata in Postgres; large artifacts (screenshot/html/trace) live in MinIO,
    # referenced here only by object key (MASTER_SPEC section 10)
    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("runs.id"), nullable=False)
    run_step_id: Mapped[str] = mapped_column(String, ForeignKey("run_steps.id"), nullable=True)

    source_url: Mapped[str] = mapped_column(String, nullable=False)
    page_title: Mapped[str] = mapped_column(String, nullable=True)
    captured_at: Mapped[str] = mapped_column(String, nullable=False)

    screenshot_object_key: Mapped[str] = mapped_column(String, nullable=True)
    html_object_key: Mapped[str] = mapped_column(String, nullable=True)
    text_snippet: Mapped[str] = mapped_column(Text, nullable=True)
    selector: Mapped[str] = mapped_column(String, nullable=True)
    field: Mapped[str] = mapped_column(String, nullable=True)

    confidence: Mapped[float] = mapped_column(Float, nullable=True)
    validation_status: Mapped[str] = mapped_column(String, default="unvalidated")

    # retention (engineering guidelines, section 10 / product spec section 10): only the
    # MinIO object is ever purged - this metadata row (URL, timestamp,
    # selector, confidence, validation result) stays queryable forever.
    artifact_purged: Mapped[bool] = mapped_column(default=False, nullable=False)
