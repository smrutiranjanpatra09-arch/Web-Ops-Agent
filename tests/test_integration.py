# end-to-end integration tests against the REAL running stack (Docker Compose:
# postgres, redis, minio, mock-site, api, worker, browser-worker). Runs the full
# task -> plan -> browse -> extract -> snapshot -> compare -> reason ->
# complete/review pipeline through the actual HTTP API, exactly the same path
# a real user/schedule would take - no shortcuts, no direct DB/module calls.
#
# Requires the stack to be up: `docker compose up -d postgres redis minio
# mock-site api worker browser-worker` and a Source+SourcePolicy row for
# mock-site:5050 already seeded (see docs/testing.md).
from __future__ import annotations

import os
import time

import pytest
import requests

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")
TERMINAL_STATES = {"COMPLETED", "REVIEW_REQUIRED"}
POLL_TIMEOUT_SECONDS = 30


@pytest.fixture(scope="module", autouse=True)
def _ensure_stack_reachable():
    try:
        res = requests.get(f"{API_BASE}/api/health", timeout=3)
        res.raise_for_status()
        body = res.json()
        if body.get("status") != "ok":
            pytest.skip(f"backend stack reports unhealthy services: {body}")
    except Exception as exc:
        pytest.skip(f"backend API not reachable at {API_BASE} - start the stack first ({exc})")


def _wait_for_terminal_state(run_id: str) -> dict:
    deadline = time.monotonic() + POLL_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        run = requests.get(f"{API_BASE}/api/runs/{run_id}", timeout=5).json()
        if run["state"] in TERMINAL_STATES or run["state"] == "FAILED":
            return run
        time.sleep(1)
    pytest.fail(f"run {run_id} did not reach a terminal state within {POLL_TIMEOUT_SECONDS}s")


def _create_task_and_run(workflow_type: str, entity_key: str, target_url: str) -> dict:
    task = requests.post(f"{API_BASE}/api/tasks", json={
        "objective": f"Integration test for {workflow_type}",
        "workflow_type": workflow_type,
        "entity_key": entity_key,
        "target_url": target_url,
    }, timeout=5).json()
    run = requests.post(f"{API_BASE}/api/runs", json={"task_id": task["id"]}, timeout=5).json()
    return _wait_for_terminal_state(run["id"])


WORKFLOWS = [
    ("hotel_pricing_watch", "Goa", "http://mock-site:5050/hotels/Goa"),
    ("campaign_page_monitoring", "monsoon-getaway", "http://mock-site:5050/campaign/monsoon-getaway"),
    ("competitor_offer_tracking", "RivalTrip", "http://mock-site:5050/competitor/RivalTrip"),
    ("partner_update_review", "Coastal Resorts Group", "http://mock-site:5050/partner/Coastal Resorts Group"),
    ("travel_trend_scanning", "all-destinations", "http://mock-site:5050/trends"),
]


@pytest.mark.parametrize("workflow_type,entity_key,target_url", WORKFLOWS)
def test_workflow_completes_end_to_end_through_real_api(workflow_type, entity_key, target_url):
    run = _create_task_and_run(workflow_type, entity_key, target_url)
    assert run["state"] in TERMINAL_STATES, (
        f"unexpected terminal state {run['state']} (error={run.get('error_type')}: {run.get('error_message')})"
    )

    results = requests.get(f"{API_BASE}/api/runs/{run['id']}/results", timeout=5).json()
    assert len(results["snapshots"]) > 0, "expected at least one extracted+snapshotted record"
    assert len(results["changes"]) > 0, "expected at least one deterministic comparison result"


def test_run_evidence_is_real_playwright_output_not_fabricated():
    # this is the specific test the engineering guidelines, section 12, call for: proof that
    # workflow data comes from Playwright execution, not an LLM/search
    # shortcut. A fabricated result would have no evidence row, no real
    # source_url matching the target, and no MinIO-backed screenshot key.
    run = _create_task_and_run("hotel_pricing_watch", "Goa", "http://mock-site:5050/hotels/Goa")
    assert run["state"] in TERMINAL_STATES

    evidence = requests.get(f"{API_BASE}/api/runs/{run['id']}/evidence", timeout=5).json()
    assert len(evidence) >= 1
    ev = evidence[0]
    assert ev["source_url"] == "http://mock-site:5050/hotels/Goa"
    assert ev["screenshot_object_key"], "no screenshot object key - browser never actually captured a page"
    assert ev["html_object_key"], "no HTML object key - browser never actually captured page content"

    # fetch the real screenshot bytes through the evidence proxy and confirm
    # they're a genuine, non-trivial PNG - not an empty/placeholder file
    screenshot = requests.get(f"{API_BASE}{ev['screenshot_url']}", timeout=10)
    assert screenshot.status_code == 200
    assert screenshot.headers["content-type"] == "image/png"
    assert len(screenshot.content) > 10_000, "screenshot suspiciously small for a real full-page capture"
    assert screenshot.content[:8] == b"\x89PNG\r\n\x1a\n", "response is not a real PNG file"


def test_second_run_compares_against_first_run_not_just_new_listings():
    # first run has no prior snapshot so everything is "new_listing"; a
    # second run for the same entity must find the first run as its baseline
    # and produce a real comparison, not silently treat everything as new again
    run1 = _create_task_and_run("competitor_offer_tracking", "OtherBooking", "http://mock-site:5050/competitor/OtherBooking")
    assert run1["state"] in TERMINAL_STATES

    run2 = _create_task_and_run("competitor_offer_tracking", "OtherBooking", "http://mock-site:5050/competitor/OtherBooking")
    assert run2["state"] in TERMINAL_STATES

    results2 = requests.get(f"{API_BASE}/api/runs/{run2['id']}/results", timeout=5).json()
    change_types = {c["change_type"] for c in results2["changes"]}
    assert change_types != {"new_listing"}, (
        "second run failed to find the first run as a comparison baseline "
        "(everything reported as new_listing again)"
    )


def test_run_model_calls_are_recorded_and_traceable():
    # Phase 29 (AI Visibility Layer): every LLM call must be automatically
    # logged via the single call_structured() choke point, regardless of
    # whether the call succeeds or falls back (e.g. rate-limited). Verifies
    # the real audit trail exists for a real run, not just that the pipeline
    # still works when the LLM path fails.
    run = _create_task_and_run("hotel_pricing_watch", "Goa", "http://mock-site:5050/hotels/Goa")
    assert run["state"] in TERMINAL_STATES

    calls = requests.get(f"{API_BASE}/api/runs/{run['id']}/model-calls", timeout=5).json()
    assert calls, "expected at least one model_invocations row (planner always calls call_structured)"

    planner_calls = [c for c in calls if c["node"] == "planner"]
    assert planner_calls, "planner node should always attempt a structured LLM call"
    for call in calls:
        assert call["run_id"] == run["id"]
        assert call["provider"] in ("gemini", "ollama")
        assert call["latency_ms"] >= 0
        # a call is never recorded as both successful AND a fallback trigger
        assert not (call["success"] and call["fallback_triggered"])
        if not call["success"]:
            assert call["error_message"], "a failed call must record why it failed"


def test_second_run_baseline_covers_every_record_not_just_one():
    # regression test: get_previous_snapshot() used to return only ONE
    # arbitrary prior Snapshot row per entity_key, even when a workflow
    # extracts many records under the same entity_key (e.g. 23 hotels all
    # under city "Goa"). Per-record diffing then matched at most 1 of N
    # records against that single row and reported the other N-1 as
    # "new_listing" every run, even though they were already seen. Fixed by
    # having the baseline lookup return every Snapshot row from the most
    # recent prior run for this entity+workflow.
    entity = "Goa"
    run1 = _create_task_and_run("hotel_pricing_watch", entity, f"http://mock-site:5050/hotels/{entity}")
    assert run1["state"] in TERMINAL_STATES

    run2 = _create_task_and_run("hotel_pricing_watch", entity, f"http://mock-site:5050/hotels/{entity}")
    assert run2["state"] in TERMINAL_STATES

    results2 = requests.get(f"{API_BASE}/api/runs/{run2['id']}/results", timeout=5).json()
    changes = results2["changes"]
    assert len(changes) > 1, "expected multiple hotel records in this comparison"
    new_listing_count = sum(1 for c in changes if c["change_type"] == "new_listing")
    assert new_listing_count == 0, (
        f"{new_listing_count}/{len(changes)} records reported as new_listing on a second run "
        "against the same unchanged entity - the comparison baseline lost records"
    )


def test_change_rows_link_back_to_the_real_snapshots_they_diffed():
    # regression test: Change.current_snapshot_id/previous_snapshot_id were
    # never populated (orchestrator's compare_node never passed them to
    # compare_and_persist) even though the real Snapshot rows existed -
    # breaking the evidence chain's Change->Snapshot link required by
    # the engineering guidelines, section 7 ("every signal must trace backward to a real
    # browser-derived observation").
    entity = "Jaipur"
    run1 = _create_task_and_run("hotel_pricing_watch", entity, f"http://mock-site:5050/hotels/{entity}")
    assert run1["state"] in TERMINAL_STATES

    run2 = _create_task_and_run("hotel_pricing_watch", entity, f"http://mock-site:5050/hotels/{entity}")
    assert run2["state"] in TERMINAL_STATES

    results2 = requests.get(f"{API_BASE}/api/runs/{run2['id']}/results", timeout=5).json()
    changes = results2["changes"]
    assert len(changes) > 1, "expected multiple hotel records in this comparison"

    for change in changes:
        assert change.get("current_snapshot_id"), (
            f"{change['entity_name']}: current_snapshot_id is missing - "
            "Change row is not linked back to the Snapshot it was computed from"
        )
        assert change.get("previous_snapshot_id"), (
            f"{change['entity_name']}: previous_snapshot_id is missing - "
            "Change row is not linked back to its comparison baseline"
        )


def test_policy_restricted_domain_is_rejected_before_any_browsing():
    # a target_url whose domain isn't in the Source registry must fail with
    # POLICY_RESTRICTED and produce zero evidence - never silently browse
    # an unapproved domain
    run = _create_task_and_run("hotel_pricing_watch", "Nowhere", "http://not-an-approved-domain.example/hotels/Nowhere")
    assert run["state"] == "FAILED"
    assert run["error_type"] == "POLICY_RESTRICTED"

    evidence = requests.get(f"{API_BASE}/api/runs/{run['id']}/evidence", timeout=5).json()
    assert evidence == [], "policy-restricted run must never produce browser evidence"
