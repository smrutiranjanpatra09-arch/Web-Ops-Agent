from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.session import Base
from backend.app.models.base import TimestampMixin, new_uuid


class Plan(Base, TimestampMixin):
    __tablename__ = "plans"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    task_id: Mapped[str] = mapped_column(String, ForeignKey("tasks.id"), nullable=False)
    objective: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="ready")  # ready | approved | rejected
    risk_notes: Mapped[str] = mapped_column(Text, nullable=True)
    stop_conditions: Mapped[str] = mapped_column(String, default="")
    rejection_reason: Mapped[str] = mapped_column(String, nullable=True)

    steps: Mapped[list["PlanStep"]] = relationship(back_populates="plan", cascade="all, delete-orphan", order_by="PlanStep.step_order")


class PlanStep(Base):
    __tablename__ = "plan_steps"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    plan_id: Mapped[str] = mapped_column(String, ForeignKey("plans.id"), nullable=False)
    step_order: Mapped[int] = mapped_column(default=0)
    action: Mapped[str] = mapped_column(String, nullable=False)  # navigate | extract | wait | click | fill
    target: Mapped[str] = mapped_column(String, nullable=False)
    notes: Mapped[str] = mapped_column(String, nullable=True)

    plan: Mapped["Plan"] = relationship(back_populates="steps")
