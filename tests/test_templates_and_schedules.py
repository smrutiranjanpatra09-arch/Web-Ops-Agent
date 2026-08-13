# task templates and recurrence schedules against the real running stack -
# the reusable-workflow layer (MASTER_SPEC section 19). Requires the api
# service up and a Source row for mock-site:5050 (category=hotel_pricing_watch)
# already seeded, matching what resolve_task_source() looks up by.
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


@pytest.fixture(scope="module")
def auth_headers():
    # schedule creation/deletion is role-gated (administrator/operations_owner) -
    # these tests need a real token, not just backend reachability
    resp = requests.post(f"{API_BASE}/api/auth/login", json={
        "email": "admin@makemytrip.demo", "password": "#demoday26",
    }, timeout=5)
    if resp.status_code != 200:
        pytest.skip("admin demo user not seeded - run backend/seed_users.py first")
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def hotel_template():
    resp = requests.post(f"{API_BASE}/api/templates", json={
        "name": "Test Hotel Pricing Watch",
        "workflow_type": "hotel_pricing_watch",
        "path_template": "/hotels/{entity}",
        "objective_template": "Track hotel pricing for {entity}",
        "wait_selector": ".hotel-card",
        "default_frequency": "hourly",
    }, timeout=5)
    resp.raise_for_status()
    return resp.json()


def test_template_creation_and_retrieval(hotel_template):
    fetched = requests.get(f"{API_BASE}/api/templates/{hotel_template['id']}", timeout=5).json()
    assert fetched["workflow_type"] == "hotel_pricing_watch"
    assert fetched["path_template"] == "/hotels/{entity}"
    assert fetched["wait_selector"] == ".hotel-card"


def test_schedule_creation_persists_with_correct_fields(hotel_template, auth_headers):
    resp = requests.post(f"{API_BASE}/api/schedules", json={
        "template_id": hotel_template["id"],
        "workflow_type": "hotel_pricing_watch",
        "entity_key": "Goa",
        "frequency": "daily",
    }, headers=auth_headers, timeout=5)
    resp.raise_for_status()
    schedule = resp.json()

    assert schedule["frequency"] == "daily"
    assert schedule["enabled"] is True
    assert schedule["last_run_id"] is None

    schedules = requests.get(f"{API_BASE}/api/schedules", timeout=5).json()
    assert any(s["id"] == schedule["id"] for s in schedules)

    requests.delete(f"{API_BASE}/api/schedules/{schedule['id']}", headers=auth_headers, timeout=5)


def test_manual_trigger_creates_real_run_and_updates_last_run(hotel_template, auth_headers):
    resp = requests.post(f"{API_BASE}/api/schedules", json={
        "template_id": hotel_template["id"],
        "workflow_type": "hotel_pricing_watch",
        "entity_key": "Goa",
        "frequency": "hourly",
    }, headers=auth_headers, timeout=5)
    schedule = resp.json()

    trigger = requests.post(f"{API_BASE}/api/schedules/{schedule['id']}/trigger", timeout=10)
    trigger.raise_for_status()
    run_id = trigger.json()["run_id"]
    assert run_id

    run = requests.get(f"{API_BASE}/api/runs/{run_id}", timeout=5).json()
    assert run["state"] != "CREATED", "trigger should have at least enqueued the run"

    updated_schedule = requests.get(f"{API_BASE}/api/schedules", timeout=5).json()
    matching = next(s for s in updated_schedule if s["id"] == schedule["id"])
    assert matching["last_run_id"] == run_id

    delete_resp = requests.delete(f"{API_BASE}/api/schedules/{schedule['id']}", headers=auth_headers, timeout=5)
    delete_resp.raise_for_status()


def test_deleting_a_schedule_with_real_runs_disables_it_instead_of_500ing(hotel_template, auth_headers):
    # regression test: DELETE /api/schedules/{id} used to hard-delete
    # unconditionally, which raised an unhandled IntegrityError (bare 500)
    # for any schedule that had already triggered a real run, since
    # runs.schedule_id references it - meaning a schedule could never be
    # deleted once used, the single most common real-world case. Fixed to
    # disable instead of delete when runs exist, preserving audit history.
    resp = requests.post(f"{API_BASE}/api/schedules", json={
        "template_id": hotel_template["id"],
        "workflow_type": "hotel_pricing_watch",
        "entity_key": "Goa",
        "frequency": "hourly",
    }, headers=auth_headers, timeout=5)
    schedule = resp.json()

    trigger = requests.post(f"{API_BASE}/api/schedules/{schedule['id']}/trigger", timeout=10)
    trigger.raise_for_status()

    delete_resp = requests.delete(f"{API_BASE}/api/schedules/{schedule['id']}", headers=auth_headers, timeout=5)
    assert delete_resp.status_code == 200, (
        f"expected a clean response, got {delete_resp.status_code}: {delete_resp.text}"
    )
    body = delete_resp.json()
    assert body.get("deleted") is False
    assert body.get("disabled") == schedule["id"]

    updated = requests.get(f"{API_BASE}/api/schedules", timeout=5).json()
    matching = next(s for s in updated if s["id"] == schedule["id"])
    assert matching["enabled"] is False


def test_unknown_template_returns_404_not_a_silent_failure(hotel_template, auth_headers):
    resp = requests.post(f"{API_BASE}/api/schedules", json={
        "template_id": "does-not-exist",
        "workflow_type": "hotel_pricing_watch",
        "entity_key": "Goa",
        "frequency": "daily",
    }, headers=auth_headers, timeout=5)
    assert resp.status_code == 404


def test_invalid_frequency_rejected(hotel_template, auth_headers):
    resp = requests.post(f"{API_BASE}/api/schedules", json={
        "template_id": hotel_template["id"],
        "workflow_type": "hotel_pricing_watch",
        "entity_key": "Goa",
        "frequency": "every-other-tuesday",
    }, headers=auth_headers, timeout=5)
    assert resp.status_code == 400


def test_schedule_mutation_rejected_without_auth(hotel_template):
    resp = requests.post(f"{API_BASE}/api/schedules", json={
        "template_id": hotel_template["id"],
        "workflow_type": "hotel_pricing_watch",
        "entity_key": "Goa",
        "frequency": "daily",
    }, timeout=5)
    assert resp.status_code == 401
