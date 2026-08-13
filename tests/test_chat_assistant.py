# Phase 31: Ask-MMT assistant - deterministic retrieval gates whether a reply
# is grounded in real monitored data vs. general LLM knowledge. Real HTTP
# calls against the running stack, same pattern as test_run_lifecycle.py.
from __future__ import annotations

import os

import pytest
import requests

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="module", autouse=True)
def _ensure_stack_reachable():
    try:
        requests.get(f"{API_BASE}/api/health", timeout=3).raise_for_status()
    except Exception as exc:
        pytest.skip(f"backend API not reachable at {API_BASE} ({exc})")


def test_retrieval_finds_nothing_for_nonsense_query():
    from backend.app.database.session import SessionLocal
    from intelligence.chat.retrieval import find_relevant_context

    db = SessionLocal()
    try:
        result = find_relevant_context(db, "zzqxw nonexistent gibberish term")
        assert result is None
    finally:
        db.close()


def test_chat_message_persists_and_reloads():
    resp = requests.post(f"{API_BASE}/api/chat/message", json={"message": "hello there"}, timeout=30)
    assert resp.status_code == 200
    body = resp.json()
    assert "session_id" in body
    assert "reply" in body
    assert body["source_type"] in ("internal_data", "general_knowledge")

    transcript = requests.get(f"{API_BASE}/api/chat/sessions/{body['session_id']}/messages", timeout=5)
    assert transcript.status_code == 200
    messages = transcript.json()["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "hello there"
    assert messages[1]["role"] == "assistant"


def test_chat_message_continues_existing_session():
    first = requests.post(f"{API_BASE}/api/chat/message", json={"message": "first message"}, timeout=30).json()
    second = requests.post(
        f"{API_BASE}/api/chat/message",
        json={"session_id": first["session_id"], "message": "second message"}, timeout=30,
    ).json()
    assert second["session_id"] == first["session_id"]

    transcript = requests.get(
        f"{API_BASE}/api/chat/sessions/{first['session_id']}/messages", timeout=5,
    ).json()
    assert len(transcript["messages"]) == 4


def test_empty_message_rejected():
    resp = requests.post(f"{API_BASE}/api/chat/message", json={"message": "   "}, timeout=5)
    assert resp.status_code == 400


def test_unknown_session_transcript_404():
    resp = requests.get(f"{API_BASE}/api/chat/sessions/nonexistent-id/messages", timeout=5)
    assert resp.status_code == 404
