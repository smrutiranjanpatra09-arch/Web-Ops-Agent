from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.session import Base
from backend.app.models.base import TimestampMixin, new_uuid


class Schedule(Base, TimestampMixin):
    __tablename__ = "schedules"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    template_id: Mapped[str] = mapped_column(String, ForeignKey("task_templates.id"), nullable=False)
    workflow_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_key: Mapped[str] = mapped_column(String, nullable=False)
    frequency: Mapped[str] = mapped_column(String, nullable=False)
    # one_time | hourly | daily | weekly | campaign_driven | event_triggered
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    owner_team: Mapped[str] = mapped_column(String, nullable=True)
    last_run_id: Mapped[str] = mapped_column(String, nullable=True)
    last_run_at: Mapped[str] = mapped_column(String, nullable=True)
