from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.models.run import Run
from browser.executor import execute_browse_step
from logger import get_logger
from mcp.schemas import ToolResult

log = get_logger("mcp.browser_tools")


def navigate(db: Session, run: Run, target_url: str, wait_selector: str) -> ToolResult:
    # policy-checked, logged wrapper around the real Playwright execution
    # path (browser/executor.py) - this is the ONLY way the orchestration
    # graph is allowed to touch the browser (MASTER_SPEC section 12/15)
    log.info(f"run={run.id} tool=navigate target={target_url}")
    success, evidence, error_type, full_html = execute_browse_step(db, run, target_url, wait_selector)
    if not success:
        log.warning(f"run={run.id} tool=navigate failed error_type={error_type}")
        return ToolResult(success=False, error_type=error_type, message=f"Navigation failed: {error_type}")
    return ToolResult(success=True, data={
        "evidence_id": evidence.id,
        "source_url": evidence.source_url,
        "page_title": evidence.page_title,
        "html_object_key": evidence.html_object_key,
        "screenshot_object_key": evidence.screenshot_object_key,
        "text_snippet": evidence.text_snippet,
        "full_html": full_html,
        "captured_at": evidence.captured_at,
    })
