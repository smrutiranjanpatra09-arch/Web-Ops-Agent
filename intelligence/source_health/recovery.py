from __future__ import annotations

import time

from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from backend.app.models.failure import Failure, RecoveryAttempt
from backend.app.models.source import Source
from logger import get_logger

log = get_logger("intelligence.recovery")

RECOVERY_POLL_TIMEOUT_SECONDS = 20
RECOVERY_POLL_INTERVAL_SECONDS = 0.5

# candidate selectors tried in order for each workflow when the configured
# selector stops matching - a real (if simple) self-healing strategy, not a
# guess-and-hope: each candidate is validated by actually re-navigating
# before being accepted (see attempt_selector_recovery)
CANDIDATE_SELECTORS = {
    "hotel_pricing_watch": [".hotel-card", "[data-hotel-name]", ".hotel-grid > div"],
    "campaign_page_monitoring": [".campaign-hero", "[data-campaign-slug]", ".campaign-card"],
    "competitor_offer_tracking": [".offer-card", "[data-competitor-name]"],
    "partner_update_review": [".update-item", "[data-partner-name]"],
    "travel_trend_scanning": [".trend-item", "[data-destination]", "[data-page='trends']"],
}

MAX_RECOVERY_ATTEMPTS = 2

# cap how many tag/class names we extract from the failed page so the
# structured description handed to the LLM stays compact (engineering guidelines, section
# 5: send targeted structured data, never raw HTML dumps).
MAX_STRUCTURE_ELEMENTS = 20


def describe_page_structure(html: str) -> dict:
    # deterministically extracts tag names + class names near the top of the
    # failed page via BeautifulSoup - this structured summary is what gets
    # sent to the LLM, never the raw HTML (engineering guidelines, section 5/8: page
    # content is untrusted data, and prompts must stay compact/structured).
    soup = BeautifulSoup(html or "", "html.parser")
    elements = []
    for tag in soup.find_all(True, limit=MAX_STRUCTURE_ELEMENTS * 3):
        classes = tag.get("class") or []
        if not classes and tag.name in ("html", "head", "body", "script", "style", "meta", "link"):
            continue
        elements.append({"tag": tag.name, "classes": classes[:5]})
        if len(elements) >= MAX_STRUCTURE_ELEMENTS:
            break
    return {"element_count": len(elements), "elements": elements}


def propose_llm_selector_candidate(structure: dict, workflow_type: str) -> str | None:
    # asks Gemini (node="recovery") for ONE additional candidate selector,
    # given only the deterministic structural description above - never the
    # raw HTML. The result is just a string suggestion; it carries no
    # special trust and must pass through the exact same
    # re-navigate-and-validate path as the hardcoded candidates before ever
    # being accepted (see attempt_selector_recovery below).
    try:
        from agents.llm import call_structured
    except Exception:
        return None

    system = (
        "You are the recovery-reasoning module of a governed web operations agent. "
        "A CSS selector used to monitor a webpage has stopped matching. You are given "
        "a deterministic, already-extracted structural summary (tag names and CSS "
        "classes found near the top of the page) - not the raw page content. Propose "
        "ONE plausible replacement CSS selector for the same kind of repeating content "
        "block. Return ONLY JSON: {\"selector\": \"<css selector>\"}"
    )
    user = (
        f"Workflow: {workflow_type}\n"
        f"Elements observed (tag + up to 5 classes each): {structure.get('elements', [])}"
    )
    try:
        raw = call_structured(system, user, node="recovery", purpose=f"Propose recovery selector for {workflow_type}")
        selector = raw.get("selector")
        if isinstance(selector, str) and selector.strip():
            return selector.strip()
        return None
    except Exception:
        log.warning("LLM recovery selector proposal failed; continuing with hardcoded candidates only", exc_info=True)
        return None


def record_failure(db: Session, *, run_id: str, run_step_id: str | None, error_type: str,
                    message: str, retryable: bool) -> Failure:
    failure = Failure(run_id=run_id, run_step_id=run_step_id, error_type=error_type,
                       message=message, retryable=retryable, recovery_state="none")
    db.add(failure)
    db.flush()
    return failure


def attempt_selector_recovery(db: Session, *, run_id: str, failure: Failure, workflow_type: str,
                              target_url: str, original_selector: str,
                              failed_page_html: str | None = None) -> tuple[bool, str | None]:
    # bounded self-healing (MASTER_SPEC section 13): try each candidate
    # selector, in order, by actually re-navigating and checking it matches -
    # never silently accept an unvalidated replacement. Stops after
    # MAX_RECOVERY_ATTEMPTS regardless of how many candidates remain.
    # Playwright only runs in browser-worker (engineering guidelines, section 10), so each
    # candidate is dispatched through the same browser queue browse_node uses,
    # not called in-process.
    from browser.jobs import enqueue_browse, get_browser_queue

    failure.recovery_state = "attempted"
    db.add(failure)
    db.flush()

    candidates = [s for s in CANDIDATE_SELECTORS.get(workflow_type, []) if s != original_selector]

    # optional LLM-suggested candidate, appended after the hardcoded list -
    # it is never inserted ahead of validated defaults and goes through the
    # identical re-navigate-and-validate loop below, so it can never be
    # "trusted blindly" (Phase 30.2 / MASTER_SPEC section 13).
    if failed_page_html:
        structure = describe_page_structure(failed_page_html)
        llm_candidate = propose_llm_selector_candidate(structure, workflow_type)
        if llm_candidate and llm_candidate not in candidates and llm_candidate != original_selector:
            candidates = candidates + [llm_candidate]

    for attempt_num, candidate in enumerate(candidates[:MAX_RECOVERY_ATTEMPTS], start=1):
        log.info(f"run={run_id} recovery attempt {attempt_num}: trying selector '{candidate}'")

        job_id = enqueue_browse(run_id, target_url, candidate)
        job = get_browser_queue().fetch_job(job_id)
        deadline = time.monotonic() + RECOVERY_POLL_TIMEOUT_SECONDS
        while job.get_status() not in ("finished", "failed") and time.monotonic() < deadline:
            time.sleep(RECOVERY_POLL_INTERVAL_SECONDS)
            job.refresh()

        succeeded = job.get_status() == "finished" and job.result.get("success")

        recovery = RecoveryAttempt(
            run_id=run_id, failure_id=failure.id, original_strategy=original_selector,
            recovery_strategy="candidate_selector", candidate_selector=candidate,
            result="validated" if succeeded else "rejected",
            confidence=0.6 if succeeded else 0.0,
        )
        db.add(recovery)
        db.flush()

        if succeeded:
            failure.recovery_state = "recovered"
            db.add(failure)
            db.flush()
            log.info(f"run={run_id} recovery succeeded with selector '{candidate}'")
            return True, candidate

    failure.recovery_state = "exhausted"
    db.add(failure)
    db.flush()
    log.warning(f"run={run_id} recovery exhausted after {len(candidates[:MAX_RECOVERY_ATTEMPTS])} attempt(s)")
    return False, None


def mark_review_required(db: Session, source: Source, *, reason: str) -> None:
    # major/repeated structural failures escalate the source itself to
    # REVIEW_REQUIRED, independent of the per-run consecutive_failures
    # counter already tracked in browser/executor.py
    source.health_state = "REVIEW_REQUIRED"
    db.add(source)
    log.warning(f"source={source.domain} escalated to REVIEW_REQUIRED: {reason}")
