from __future__ import annotations

from pydantic import BaseModel


class ChatMessageRequest(BaseModel):
    session_id: str | None = None
    message: str


class ChatMessageResponse(BaseModel):
    session_id: str
    reply: str
    grounded: bool
    source_type: str
    evidence_refs: list[str]


class ChatMessageItem(BaseModel):
    id: str
    role: str
    content: str
    grounded: bool
    source_type: str | None
    evidence_refs: list[str]
    created_at: str


class ChatTranscriptResponse(BaseModel):
    session_id: str
    messages: list[ChatMessageItem]
