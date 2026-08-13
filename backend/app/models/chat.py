from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.session import Base
from backend.app.models.base import TimestampMixin, new_uuid


class ChatSession(Base, TimestampMixin):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=True)


class ChatMessage(Base, TimestampMixin):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    session_id: Mapped[str] = mapped_column(String, ForeignKey("chat_sessions.id"), nullable=False)

    role: Mapped[str] = mapped_column(String, nullable=False)  # user | assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    grounded: Mapped[bool] = mapped_column(Boolean, default=False)
    source_type: Mapped[str] = mapped_column(String, nullable=True)  # internal_data | general_knowledge
    evidence_refs: Mapped[str] = mapped_column(Text, nullable=True)  # small JSON string: signal_ids/change_ids
    model_invocation_id: Mapped[str] = mapped_column(String, ForeignKey("model_invocations.id"), nullable=True)
