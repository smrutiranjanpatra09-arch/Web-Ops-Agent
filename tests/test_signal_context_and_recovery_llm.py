# Phase 30 tests:
# - historical_context is computed deterministically (context_builder.py),
#   never by the LLM (engineering guidelines, section 6)
# - an LLM-suggested recovery selector still goes through the exact same
#   validation path as hardcoded candidates (never trusted blindly)
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.database.session import Base
from backend.app.models.snapshot import Change
from intelligence.signals.context_builder import build_signal_context, summarize_historical_context


@pytest.fixture()
def db_session():
    # isolated in-memory SQLite DB per test - no Postgres/Docker required for
    # this deterministic unit test (only Change rows are needed).
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[Change.__table__])
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def _make_change(entity_name="Taj Hotel", entity_key="Mumbai", change_type="price_increase",
                  days_ago=0, run_id="run-1"):
    return Change(
        run_id=run_id, entity_name=entity_name, entity_key=entity_key, change_type=change_type,
        previous_value="1000", current_value="1100", abs_diff=100, delta_pct=10.0,
        significance="notable", business_relevant=True,
        created_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
    )


def test_build_signal_context_computes_frequency_deterministically(db_session):
    # 4 prior price_increase changes + this one => 5th occurrence, computed in
    # plain python from real rows, no LLM involved anywhere in this path.
    for days_ago in (6, 5, 3, 1):
        db_session.add(_make_change(days_ago=days_ago))
    db_session.flush()

    current = _make_change(days_ago=0)
    db_session.add(current)
    db_session.flush()

    context = build_signal_context(db_session, current)

    assert context["occurrence_count_same_type"] == 5
    assert context["direction_streak"] == 5
    assert context["history_window_size"] == 4
    assert context["has_sufficient_history"] is False  # only 4 prior rows, window is 5


def test_build_signal_context_ignores_other_entities(db_session):
    db_session.add(_make_change(entity_name="Other Hotel", entity_key="Delhi", days_ago=2))
    db_session.flush()
    current = _make_change(days_ago=0)
    db_session.add(current)
    db_session.flush()

    context = build_signal_context(db_session, current)
    assert context["occurrence_count_same_type"] == 1
    assert context["history_window_size"] == 0


def test_summarize_historical_context_is_pure_python_not_llm():
    # no network/LLM call is even reachable from this function signature -
    # it only takes the already-computed dict and does string formatting.
    context = {
        "occurrence_count_same_type": 3,
        "entity_name": "Taj Hotel",
        "change_type": "price_increase",
        "window_days": 7,
    }
    text = summarize_historical_context(context)
    assert "3rd" in text
    assert "Taj Hotel" in text
    assert "7 day" in text


def test_first_occurrence_context_reads_naturally():
    context = {
        "occurrence_count_same_type": 1,
        "entity_name": "Taj Hotel",
        "change_type": "price_increase",
        "window_days": None,
    }
    text = summarize_historical_context(context)
    assert "First recorded" in text


# --- recovery LLM candidate: must go through the same validation path ---

from intelligence.source_health import recovery as recovery_module  # noqa: E402
from backend.app.models.failure import Failure, RecoveryAttempt  # noqa: E402


SAMPLE_HTML = """
<html><body>
<div class="hotel-listing-row" data-hotel="1">Taj Hotel</div>
<div class="hotel-listing-row" data-hotel="2">Oberoi</div>
</body></html>
"""


def test_describe_page_structure_is_deterministic_bs4_extraction():
    structure = recovery_module.describe_page_structure(SAMPLE_HTML)
    tags = [e["tag"] for e in structure["elements"]]
    assert "div" in tags
    assert structure["element_count"] > 0


def test_llm_suggested_selector_goes_through_same_validation_as_hardcoded(monkeypatch):
    # mock the LLM to propose a novel selector, and mock the browser-queue
    # dispatch that every candidate (hardcoded or LLM-suggested) must pass
    # through via enqueue_browse/get_browser_queue - assert the LLM candidate
    # is attempted through that exact same re-navigate+validate loop, not
    # accepted directly from the LLM response.
    with patch("intelligence.source_health.recovery.propose_llm_selector_candidate",
               return_value=".hotel-listing-row"):

        calls = []

        class FakeJob:
            def __init__(self, selector):
                self.selector = selector

            def get_status(self):
                return "finished"

            def refresh(self):
                pass

            @property
            def result(self):
                return {"success": self.selector == ".hotel-listing-row"}

        class FakeQueue:
            def fetch_job(self, job_id):
                return FakeJob(job_id)

        def fake_enqueue_browse(run_id, target_url, selector):
            calls.append(selector)
            return selector  # job_id doubles as the selector for this fake

        with patch("browser.jobs.enqueue_browse", side_effect=fake_enqueue_browse), \
             patch("browser.jobs.get_browser_queue", return_value=FakeQueue()):

            engine = create_engine("sqlite:///:memory:")
            Base.metadata.create_all(engine, tables=[Failure.__table__, RecoveryAttempt.__table__])
            SessionLocal = sessionmaker(bind=engine)
            db = SessionLocal()

            failure = Failure(run_id="run-1", error_type="SELECTOR_NOT_FOUND",
                               message="not found", retryable=True)
            db.add(failure)
            db.flush()

            # workflow_type has no hardcoded candidates configured, so the ONLY
            # candidate under test is the LLM-suggested one - proving it still
            # goes through attempt_selector_recovery's real validation loop.
            recovery_module.CANDIDATE_SELECTORS["_test_workflow_only_llm"] = []

            recovered, candidate = recovery_module.attempt_selector_recovery(
                db, run_id="run-1", failure=failure, workflow_type="_test_workflow_only_llm",
                target_url="https://example.com/hotels", original_selector=".old-selector",
                failed_page_html=SAMPLE_HTML,
            )

    assert calls == [".hotel-listing-row"], "LLM candidate must be dispatched through the real browse queue"
    assert recovered is True
    assert candidate == ".hotel-listing-row"
    assert failure.recovery_state == "recovered"


def test_llm_selector_candidate_rejected_still_updates_recovery_state(monkeypatch):
    # if the LLM candidate fails real validation, it must be rejected exactly
    # like a bad hardcoded candidate would be - never silently accepted.
    with patch("intelligence.source_health.recovery.propose_llm_selector_candidate",
               return_value=".bogus-llm-selector"):

        class FakeJob:
            def get_status(self):
                return "finished"

            def refresh(self):
                pass

            @property
            def result(self):
                return {"success": False}

        class FakeQueue:
            def fetch_job(self, job_id):
                return FakeJob()

        with patch("browser.jobs.enqueue_browse", return_value="job-1"), \
             patch("browser.jobs.get_browser_queue", return_value=FakeQueue()):

            engine = create_engine("sqlite:///:memory:")
            Base.metadata.create_all(engine, tables=[Failure.__table__, RecoveryAttempt.__table__])
            SessionLocal = sessionmaker(bind=engine)
            db = SessionLocal()

            failure = Failure(run_id="run-2", error_type="SELECTOR_NOT_FOUND",
                               message="not found", retryable=True)
            db.add(failure)
            db.flush()

            recovery_module.CANDIDATE_SELECTORS["_test_workflow_only_llm_2"] = []

            recovered, candidate = recovery_module.attempt_selector_recovery(
                db, run_id="run-2", failure=failure, workflow_type="_test_workflow_only_llm_2",
                target_url="https://example.com/hotels", original_selector=".old-selector",
                failed_page_html=SAMPLE_HTML,
            )

    assert recovered is False
    assert candidate is None
    assert failure.recovery_state == "exhausted"
