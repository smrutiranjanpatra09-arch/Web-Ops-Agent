from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.session import Base
from backend.app.models.base import TimestampMixin, new_uuid


class AuditEvent(Base, TimestampMixin):
    # every significant action gets an audit record (engineering guidelines, section 11):
    # actor, task, run, action, timestamp, result, reason
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    task_id: Mapped[str] = mapped_column(String, ForeignKey("tasks.id"), nullable=True)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("runs.id"), nullable=True)
    actor: Mapped[str] = mapped_column(String, nullable=False)  # user:<id> | system | service_worker
    action: Mapped[str] = mapped_column(String, nullable=False)
    result: Mapped[str] = mapped_column(String, nullable=False)  # success | failure
    reason: Mapped[str] = mapped_column(Text, nullable=True)
