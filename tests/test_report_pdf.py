# Phase 35: GET /api/runs/{id}/report.pdf - real HTTP calls against the live
# stack, same pattern as test_run_lifecycle.py (health check skip, login via
# a seeded demo account, real task/run creation, wait for terminal state).
# Proves the endpoint returns real, nonempty PDF bytes rather than an empty
# shell or a JSON error disguised with the right status code.
from __future__ import annotations

import os
import time

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


@pytest.fixture(scope="module")
def admin_headers():
    resp = requests.post(
        f"{API_BASE}/api/auth/login",
        json={"email": "admin@makemytrip.demo", "password": "#demoday26"},
        timeout=5,
    )
    if resp.status_code != 200:
        pytest.skip("demo admin user not seeded - run backend/seed_users.py first")
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_and_finish_run(entity_key="Goa") -> str:
    task = requests.post(f"{API_BASE}/api/tasks", json={
        "objective": f"Phase 35 PDF report test for {entity_key}",
        "workflow_type": "hotel_pricing_watch",
        "entity_key": entity_key,
        "target_url": f"http://mock-site:5050/hotels/{entity_key}",
    }, timeout=5).json()
    run = requests.post(f"{API_BASE}/api/runs", json={"task_id": task["id"]}, timeout=5).json()

    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        current = requests.get(f"{API_BASE}/api/runs/{run['id']}", timeout=5).json()
        if current["state"] in TERMINAL_STATES:
            break
        time.sleep(1)
    return run["id"]


def test_report_pdf_requires_auth():
    run_id = _create_and_finish_run()
    resp = requests.get(f"{API_BASE}/api/runs/{run_id}/report.pdf", timeout=15)
    assert resp.status_code == 401


def test_report_pdf_returns_real_pdf_bytes(admin_headers):
    run_id = _create_and_finish_run()
    resp = requests.get(f"{API_BASE}/api/runs/{run_id}/report.pdf", headers=admin_headers, timeout=20)

    assert resp.status_code == 200
    assert resp.headers.get("content-type", "").startswith("application/pdf")
    assert resp.content.startswith(b"%PDF")
    # a real rendered report (header + digest + tables + footer) should never
    # be a near-empty shell - this catches a build that "succeeds" but emits
    # a blank/near-blank document.
    assert len(resp.content) > 2000


def test_report_pdf_404_for_unknown_run(admin_headers):
    resp = requests.get(f"{API_BASE}/api/runs/does-not-exist/report.pdf", headers=admin_headers, timeout=10)
    assert resp.status_code == 404
