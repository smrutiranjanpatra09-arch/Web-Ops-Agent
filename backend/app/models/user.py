from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.session import Base
from backend.app.models.base import TimestampMixin, new_uuid


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    # task_creator | reviewer | operations_owner | administrator | service_worker | growth_user


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    role_id: Mapped[str] = mapped_column(String, ForeignKey("roles.id"), nullable=False)

    role: Mapped["Role"] = relationship()
