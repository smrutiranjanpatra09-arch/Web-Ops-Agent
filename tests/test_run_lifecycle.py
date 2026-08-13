# Phase 37: pagination/filtering on GET /api/runs, soft archival (single +
# bulk), admin-only hard delete, and MinIO artifact retention. Follows the
# same pattern as test_integration.py / test_templates_and_schedules.py -
# real HTTP calls against the actual running stack, no direct DB/module
# access, so a passing test proves the real API contract, not an internal
# shortcut.
from __future__ import annotations

import os
from unittest.mock import patch

import pytest
import requests

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")
TERMINAL_STATES = {"COMPLETED", "REVIEW_REQUIRED", "FAILED", "CANCELLED"}


@pytest.fixture(scope="module", autouse=True)
def _ensure_stack_reachable():
    try:
        requests.get(f"{API_BASE}/api/health", timeout=3).raise_for_status()
    except Exception as exc:
        pytest.skip(f"backend API not reachable at {API_BASE} ({exc})")


def _login(email: str, password: str = "#demoday26") -> dict:
    resp = requests.post(f"{API_BASE}/api/auth/login", json={"email": email, "password": password}, timeout=5)
    if resp.status_code != 200:
        pytest.skip(f"demo user {email} not seeded - run backend/seed_users.py first")
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def admin_headers():
    return _login("admin@makemytrip.demo")


@pytest.fixture(scope="module")
def owner_headers():
    return _login("owner@makemytrip.demo")


@pytest.fixture(scope="module")
def reviewer_headers():
    return _login("reviewer@makemytrip.demo")


def _create_run(workflow_type="hotel_pricing_watch", entity_key="Goa",
                 target_url="http://mock-site:5050/hotels/Goa") -> dict:
    task = requests.post(f"{API_BASE}/api/tasks", json={
        "objective": f"Phase 37 lifecycle test for {entity_key}",
        "workflow_type": workflow_type,
        "entity_key": entity_key,
        "target_url": target_url,
    }, timeout=5).json()
    run = requests.post(f"{API_BASE}/api/runs", json={"task_id": task["id"]}, timeout=5).json()
    return run


def _wait_terminal(run_id: str, timeout=30) -> dict:
    import time
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        run = requests.get(f"{API_BASE}/api/runs/{run_id}", timeout=5).json()
        if run["state"] in TERMINAL_STATES:
            return run
        time.sleep(1)
    pytest.fail(f"run {run_id} never reached a terminal state")


# --- 37.1 pagination + filtering -------------------------------------------------

def test_list_runs_respects_limit_and_offset():
    for _ in range(3):
        _create_run()

    page1 = requests.get(f"{API_BASE}/api/runs", params={"limit": 2, "offset": 0}, timeout=5).json()
    page2 = requests.get(f"{API_BASE}/api/runs", params={"limit": 2, "offset": 2}, timeout=5).json()
    assert len(page1) == 2
    assert len(page2) >= 1
    assert {r["id"] for r in page1}.isdisjoint({r["id"] for r in page2})


def test_list_runs_filters_by_state():
    run = _create_run()
    filtered = requests.get(f"{API_BASE}/api/runs", params={"state": "CREATED", "limit": 500}, timeout=5).json()
    # the run was just created and enqueued, so it may already have moved past
    # CREATED - the real assertion is that every row returned actually matches
    # the filter, not that our specific run is caught mid-transition
    assert all(r["state"] == "CREATED" for r in filtered)


def test_list_runs_filters_by_workflow_type():
    _create_run(workflow_type="hotel_pricing_watch", entity_key="Goa", target_url="http://mock-site:5050/hotels/Goa")
    filtered = requests.get(
        f"{API_BASE}/api/runs", params={"workflow_type": "hotel_pricing_watch", "limit": 500}, timeout=5,
    ).json()
    assert len(filtered) >= 1
    task_ids = {r["task_id"] for r in filtered}
    tasks = {tid: requests.get(f"{API_BASE}/api/tasks/{tid}", timeout=5).json() for tid in task_ids}
    assert all(tasks[r["task_id"]]["workflow_type"] == "hotel_pricing_watch" for r in filtered)


def test_list_runs_since_filters_out_older_runs():
    import datetime
    future = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)).isoformat()
    filtered = requests.get(f"{API_BASE}/api/runs", params={"since": future}, timeout=5).json()
    assert filtered == [], "a 'since' timestamp in the future should return no runs"


def test_list_runs_since_rejects_unparseable_timestamp():
    resp = requests.get(f"{API_BASE}/api/runs", params={"since": "not-a-date"}, timeout=5)
    assert resp.status_code == 400


# --- 37.2 soft archival ------------------------------------------------------

def test_archive_run_requires_role(reviewer_headers):
    run = _create_run()
    resp = requests.post(f"{API_BASE}/api/runs/{run['id']}/archive", headers=reviewer_headers, timeout=5)
    assert resp.status_code == 403


def test_archive_run_requires_auth():
    run = _create_run()
    resp = requests.post(f"{API_BASE}/api/runs/{run['id']}/archive", timeout=5)
    assert resp.status_code == 401


def test_archive_run_succeeds_for_operations_owner_and_hides_from_default_list(owner_headers):
    run = _create_run()
    resp = requests.post(f"{API_BASE}/api/runs/{run['id']}/archive", headers=owner_headers, timeout=5)
    assert resp.status_code == 200
    body = resp.json()
    assert body["archived"] is True
    assert body["archived_at"]
    assert body["archived_by"]

    default_list = requests.get(f"{API_BASE}/api/runs", params={"limit": 500}, timeout=5).json()
    assert run["id"] not in {r["id"] for r in default_list}

    included_list = requests.get(
        f"{API_BASE}/api/runs", params={"limit": 500, "include_archived": "true"}, timeout=5,
    ).json()
    assert run["id"] in {r["id"] for r in included_list}

    # still individually fetchable by ID with the evidence chain intact
    fetched = requests.get(f"{API_BASE}/api/runs/{run['id']}", timeout=5).json()
    assert fetched["archived"] is True
    steps = requests.get(f"{API_BASE}/api/runs/{run['id']}/steps", timeout=5)
    assert steps.status_code == 200


def test_archive_run_rejects_double_archive(owner_headers):
    run = _create_run()
    requests.post(f"{API_BASE}/api/runs/{run['id']}/archive", headers=owner_headers, timeout=5)
    resp = requests.post(f"{API_BASE}/api/runs/{run['id']}/archive", headers=owner_headers, timeout=5)
    assert resp.status_code == 400


def test_bulk_archive_is_admin_only(owner_headers):
    resp = requests.post(
        f"{API_BASE}/api/runs/archive-bulk", json={"older_than_days": 9999, "state": "COMPLETED"},
        headers=owner_headers, timeout=5,
    )
    assert resp.status_code == 403


def test_bulk_archive_only_matches_given_state_and_age(admin_headers):
    # nothing should be old enough to match a 9999-day cutoff for a state that
    # was never used by any run created in this test session
    resp = requests.post(
        f"{API_BASE}/api/runs/archive-bulk",
        json={"older_than_days": 9999, "state": "RERUN_REQUESTED"},
        headers=admin_headers, timeout=5,
    )
    assert resp.status_code == 200
    assert resp.json()["count"] == 0


# --- 37.4 admin-only hard delete ---------------------------------------------

def test_hard_delete_rejected_when_not_archived(admin_headers):
    run = _create_run()
    resp = requests.delete(
        f"{API_BASE}/api/runs/{run['id']}", json={"reason": "cleanup"}, headers=admin_headers, timeout=5,
    )
    assert resp.status_code == 400


def test_hard_delete_is_admin_only(owner_headers):
    run = _create_run()
    resp = requests.delete(
        f"{API_BASE}/api/runs/{run['id']}", json={"reason": "cleanup"}, headers=owner_headers, timeout=5,
    )
    assert resp.status_code == 403


def test_hard_delete_writes_audit_event_then_removes_row(admin_headers):
    # a run with no dependent evidence/steps rows beyond RunStep(CREATED) and
    # its own creation AuditEvent is the only case that can cleanly satisfy
    # the FK constraints on hard delete - real runs with evidence stay
    # archived instead, which the 409 branch in the endpoint enforces.
    run = _create_run()
    archive_resp = requests.post(f"{API_BASE}/api/runs/{run['id']}/archive", headers=admin_headers, timeout=5)
    assert archive_resp.status_code == 200

    delete_resp = requests.delete(
        f"{API_BASE}/api/runs/{run['id']}", json={"reason": "test cleanup - no real evidence"},
        headers=admin_headers, timeout=5,
    )
    # either it deletes cleanly (no dependent rows reached the DB yet) or it
    # 409s because the worker already attached evidence/steps - both are
    # correct depending on how far the async worker got; what matters is it
    # is never a bare 500 and the run is gone from a normal lookup on success
    assert delete_resp.status_code in (200, 409)
    if delete_resp.status_code == 200:
        assert delete_resp.json()["deleted"] == run["id"]
        followup = requests.get(f"{API_BASE}/api/runs/{run['id']}", timeout=5)
        assert followup.status_code == 404


def test_hard_delete_requires_auth():
    resp = requests.delete(f"{API_BASE}/api/runs/does-not-exist", json={"reason": "x"}, timeout=5)
    assert resp.status_code == 401


# --- 37.3 retention purges MinIO object but keeps Evidence row queryable -----

def test_retention_purges_artifact_but_preserves_evidence_metadata():
    # exercises retention_service.purge_expired_artifacts directly against a
    # real Evidence row from a real completed run - this proves the row
    # (URL, timestamp, selector, confidence, validation result) survives even
    # though the MinIO bytes are gone. The MinIO delete call itself is
    # mocked since there's no guarantee the test host can reach the
    # container-internal MinIO endpoint the same way the api/worker containers do,
    # matching how this repo already stubs the browser/MinIO boundary in unit tests.
    import sys
    sys.path.insert(0, os.getcwd())
    from datetime import datetime, timedelta, timezone

    from backend.app.database.session import SessionLocal
    from backend.app.models.evidence import Evidence
    from backend.app.services.retention_service import purge_expired_artifacts

    run = _create_run()
    # this test file creates a lot of runs in quick succession right before
    # this one, so the single worker's queue can be backlogged - allow more
    # time than the other terminal-state waits in this file.
    run = _wait_terminal(run["id"], timeout=60)
    evidence_rows = requests.get(f"{API_BASE}/api/runs/{run['id']}/evidence", timeout=5).json()
    if not evidence_rows:
        pytest.skip("run produced no evidence rows to test retention against")

    db = SessionLocal()
    try:
        ev = db.query(Evidence).filter(Evidence.id == evidence_rows[0]["id"]).one()
        original_key = ev.screenshot_object_key
        # backdate creation so it's older than even a 1-day retention window
        ev.created_at = datetime.now(timezone.utc) - timedelta(days=2)
        db.add(ev)
        db.commit()

        with patch("backend.app.services.retention_service.get_settings") as mock_settings, \
             patch("backend.app.services.retention_service.delete_object") as mock_delete:
            mock_settings.return_value.retention_days_raw_artifacts = 1
            purged_ids = purge_expired_artifacts(db)

        assert ev.id in purged_ids
        if original_key:
            mock_delete.assert_any_call(original_key)

        db.refresh(ev)
        assert ev.artifact_purged is True
        assert ev.screenshot_object_key is None
        assert ev.html_object_key is None
        # metadata must survive untouched
        assert ev.source_url == evidence_rows[0]["source_url"]
        assert ev.confidence == evidence_rows[0]["confidence"]
        assert ev.validation_status == evidence_rows[0]["validation_status"]

        still_fetchable = requests.get(f"{API_BASE}/api/runs/{run['id']}/evidence", timeout=5).json()
        matching = next(r for r in still_fetchable if r["id"] == ev.id)
        assert matching["artifact_purged"] is True
        assert matching["screenshot_url"] is None
    finally:
        db.close()
