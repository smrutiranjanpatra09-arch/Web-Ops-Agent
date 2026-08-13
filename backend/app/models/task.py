from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.session import Base
from backend.app.models.base import TimestampMixin, new_uuid


class TaskTemplate(Base, TimestampMixin):
    __tablename__ = "task_templates"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    workflow_type: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)
    path_template: Mapped[str] = mapped_column(String, nullable=False)
    objective_template: Mapped[str] = mapped_column(String, nullable=False)
    wait_selector: Mapped[str] = mapped_column(String, nullable=False)
    expected_fields: Mapped[str] = mapped_column(String, default="")  # comma-separated
    default_frequency: Mapped[str] = mapped_column(String, default="daily")
    owner_team: Mapped[str] = mapped_column(String, nullable=True)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    stop_conditions: Mapped[str] = mapped_column(String, default="")


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    objective: Mapped[str] = mapped_column(String, nullable=False)
    workflow_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_key: Mapped[str] = mapped_column(String, nullable=False)
    template_id: Mapped[str] = mapped_column(String, ForeignKey("task_templates.id"), nullable=True)
    owner: Mapped[str] = mapped_column(String, nullable=True)
    risk_level: Mapped[str] = mapped_column(String, default="low")  # low | medium | high
    review_required: Mapped[bool] = mapped_column(Boolean, default=False)
    completion_criteria: Mapped[str] = mapped_column(String, nullable=True)

    sources: Mapped[list["TaskSource"]] = relationship(back_populates="task", cascade="all, delete-orphan")


class TaskSource(Base):
    __tablename__ = "task_sources"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    task_id: Mapped[str] = mapped_column(String, ForeignKey("tasks.id"), nullable=False)
    # source_id resolved by domain allowlist at browse time if not set here
    # explicitly (browser/policies/allowlist.py checks the target_url's domain
    # against the Source registry regardless)
    source_id: Mapped[str] = mapped_column(String, ForeignKey("sources.id"), nullable=True)
    target_url: Mapped[str] = mapped_column(String, nullable=False)

    task: Mapped["Task"] = relationship(back_populates="sources")
