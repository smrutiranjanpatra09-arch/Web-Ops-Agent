from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.app.models.evidence import Evidence
from backend.app.models.run import Run
from backend.app.models.source import Source
from browser.actions.navigate import navigate_and_capture
from browser.evidence.store import upload_html, upload_screenshot
from browser.policies.allowlist import PolicyViolation, check_domain_allowed, resolve_policy
from logger import get_logger

log = get_logger("browser.executor")


def execute_browse_step(db: Session, run: Run, target_url: str, wait_selector: str) -> tuple[bool, Evidence | None, str | None, str | None]:
    # policy check -> real browser execution -> evidence capture, in that
    # order. Returns (success, evidence_row_or_None, error_type_or_None,
    # full_html_or_None). The full HTML is returned separately from the
    # Evidence row because Evidence.text_snippet is deliberately truncated
    # for storage economy - deterministic extraction (unlike an LLM prompt)
    # needs the complete page, not a 2000-char preview.
    try:
        source = check_domain_allowed(db, target_url)
        policy = resolve_policy(db, source, target_url)
    except PolicyViolation as exc:
        log.warning(f"run={run.id} policy violation: {exc}")
        return False, None, "POLICY_RESTRICTED", None

    result = navigate_and_capture(target_url, wait_selector, timeout_seconds=policy.timeout_seconds)

    _update_source_health(db, source, success=result.success)

    if not result.success:
        log.warning(f"run={run.id} browse failed ({result.error_type}): {result.issues}")
        return False, None, result.error_type, None

    screenshot_key = None
    html_key = None
    if result.screenshot_bytes:
        screenshot_key = upload_screenshot(run.id, result.screenshot_bytes)
    if result.html_excerpt:
        html_key = upload_html(run.id, result.html_excerpt)

    evidence = Evidence(
        run_id=run.id,
        source_url=result.source_url,
        page_title=result.page_title,
        captured_at=result.captured_at,
        screenshot_object_key=screenshot_key,
        html_object_key=html_key,
        text_snippet=result.html_excerpt[:2000] if result.html_excerpt else None,
        validation_status="unvalidated",
    )
    db.add(evidence)
    db.flush()
    log.info(f"run={run.id} captured '{result.page_title}' at {result.source_url}, evidence_id={evidence.id}")
    return True, evidence, None, result.html_excerpt


def _update_source_health(db: Session, source: Source, *, success: bool) -> None:
    source.total_runs += 1
    if success:
        source.consecutive_failures = 0
    else:
        source.total_failures += 1
        source.consecutive_failures += 1
        if source.consecutive_failures >= 5:
            source.health_state = "FAILED"
        elif source.consecutive_failures >= 3:
            source.health_state = "UNSTABLE"
        elif source.consecutive_failures >= 1:
            source.health_state = "DEGRADED"
    if success and source.health_state in ("DEGRADED", "UNSTABLE"):
        source.health_state = "HEALTHY"
    db.add(source)
