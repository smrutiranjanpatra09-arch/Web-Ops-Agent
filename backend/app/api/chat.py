import json

import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.app.auth.security import decode_access_token
from backend.app.database.session import get_db
from backend.app.models.chat import ChatMessage, ChatSession
from backend.app.models.user import User
from backend.app.schemas.chat import (
    ChatMessageItem,
    ChatMessageRequest,
    ChatMessageResponse,
    ChatTranscriptResponse,
)
from intelligence.chat.retrieval import find_relevant_context

router = APIRouter(prefix="/api/chat", tags=["chat"])

_bearer = HTTPBearer(auto_error=False)

GROUNDED_SYSTEM_PROMPT = (
    "You are Ask MMT Assistant, a travel operations assistant. Using ONLY the "
    "real monitored data provided below, answer the user's question. Cite which "
    "signal or entity you used. Do not invent facts beyond what is given. Return "
    'ONLY JSON matching this shape: {"reply": "your answer, citing the data used"}'
)

GENERAL_SYSTEM_PROMPT = (
    "You are Ask MMT Assistant. You have no access to live monitoring data for "
    "this question. Answer from general travel knowledge and say explicitly that "
    "this is not from live monitoring. Return ONLY JSON matching this shape: "
    '{"reply": "your answer, stating it is general knowledge, not live data"}'
)


def _optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User | None:
    if credentials is None:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        return None
    return db.get(User, payload.get("sub"))


def _get_or_create_session(db: Session, session_id: str | None, user: User | None) -> ChatSession:
    if session_id:
        session = db.get(ChatSession, session_id)
        if session is not None:
            return session
    session = ChatSession(user_id=user.id if user else None)
    db.add(session)
    db.flush()
    return session


def _persist_message(db: Session, session_id: str, role: str, content: str, *,
                      grounded: bool = False, source_type: str | None = None,
                      evidence_refs: list[str] | None = None,
                      model_invocation_id: str | None = None) -> ChatMessage:
    message = ChatMessage(
        session_id=session_id, role=role, content=content, grounded=grounded,
        source_type=source_type, evidence_refs=json.dumps(evidence_refs or []),
        model_invocation_id=model_invocation_id,
    )
    db.add(message)
    db.flush()
    return message


@router.post("/message", response_model=ChatMessageResponse)
def send_message(payload: ChatMessageRequest, db: Session = Depends(get_db),
                  user: User | None = Depends(_optional_user)):
    if not payload.message.strip():
        raise HTTPException(400, "Message cannot be empty.")

    session = _get_or_create_session(db, payload.session_id, user)
    db.commit()
    _persist_message(db, session.id, "user", payload.message)
    db.commit()

    context = find_relevant_context(db, payload.message)
    evidence_refs: list[str] = []
    if context:
        evidence_refs = [c["id"] for c in context["changes"]] + [s["id"] for s in context["signals"]]

    try:
        from agents.llm import call_structured

        if context:
            user_prompt = f"Question: {payload.message}\n\nReal monitored data:\n{json.dumps(context)}"
            raw = call_structured(
                GROUNDED_SYSTEM_PROMPT, user_prompt, node="chat", purpose="grounded_chat_response",
                chat_session_id=session.id, input_ref_ids={"evidence_refs": evidence_refs},
            )
            grounded, source_type = True, "internal_data"
        else:
            raw = call_structured(
                GENERAL_SYSTEM_PROMPT, payload.message, node="chat", purpose="general_chat_response",
                chat_session_id=session.id,
            )
            grounded, source_type = False, "general_knowledge"
        reply = raw["reply"]
    except Exception:
        reply = "I couldn't process that right now. Please try again shortly."
        grounded, source_type, evidence_refs = False, "general_knowledge", []

    _persist_message(
        db, session.id, "assistant", reply, grounded=grounded,
        source_type=source_type, evidence_refs=evidence_refs,
    )
    db.commit()

    return ChatMessageResponse(
        session_id=session.id, reply=reply, grounded=grounded,
        source_type=source_type, evidence_refs=evidence_refs,
    )


@router.get("/sessions/{session_id}/messages", response_model=ChatTranscriptResponse)
def get_transcript(session_id: str, db: Session = Depends(get_db)):
    session = db.get(ChatSession, session_id)
    if session is None:
        raise HTTPException(404, f"Chat session '{session_id}' not found.")

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return ChatTranscriptResponse(
        session_id=session_id,
        messages=[
            ChatMessageItem(
                id=m.id, role=m.role, content=m.content, grounded=m.grounded,
                source_type=m.source_type, evidence_refs=json.loads(m.evidence_refs or "[]"),
                created_at=m.created_at.isoformat(),
            )
            for m in messages
        ],
    )
