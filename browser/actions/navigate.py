from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

# Playwright surfaces DNS/connection failures (net::ERR_NAME_NOT_RESOLVED,
# net::ERR_CONNECTION_REFUSED, net::ERR_CONNECTION_RESET, etc.) as a plain
# playwright.sync_api.Error with the reason embedded in the message, not as a
# distinct exception type - without this check they fall into the generic
# UNKNOWN bucket even though they're a textbook SOURCE_UNAVAILABLE case.
_NETWORK_ERROR_MARKERS = ("net::ERR_NAME_NOT_RESOLVED", "net::ERR_CONNECTION_REFUSED",
                          "net::ERR_CONNECTION_RESET", "net::ERR_CONNECTION_TIMED_OUT",
                          "net::ERR_ADDRESS_UNREACHABLE", "net::ERR_INTERNET_DISCONNECTED",
                          "net::ERR_UNSAFE_PORT")


def _step(action: str, target: str, status: str, detail: str | None = None) -> dict:
    return {
        "action": action, "target": target, "status": status,
        "detail": detail, "at": datetime.now(timezone.utc).isoformat(),
    }


@dataclass
class BrowserRunResult:
    success: bool
    html_excerpt: str = ""
    screenshot_bytes: bytes | None = None
    source_url: str = ""
    page_title: str = ""
    captured_at: str = ""
    issues: list[str] = field(default_factory=list)
    executed_steps: list[dict] = field(default_factory=list)
    error_type: str | None = None


def navigate_and_capture(target_url: str, wait_selector: str, *, timeout_seconds: int = 15) -> BrowserRunResult:
    # real Playwright/Chromium execution - the only source of "what's on the
    # website" per the engineering guidelines, section 4. Runs inside browser-worker only.
    issues: list[str] = []
    executed_steps: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.on("dialog", lambda d: d.dismiss())

        try:
            try:
                response = page.goto(target_url, timeout=timeout_seconds * 1000, wait_until="domcontentloaded")
            except PlaywrightError as exc:
                if any(marker in str(exc) for marker in _NETWORK_ERROR_MARKERS):
                    issues.append(f"Source unreachable: {exc}")
                    executed_steps.append(_step("navigate", target_url, "failed", str(exc)[:200]))
                    browser.close()
                    return BrowserRunResult(
                        success=False, source_url=target_url, issues=issues,
                        executed_steps=executed_steps, error_type="SOURCE_UNAVAILABLE",
                    )
                raise
            if response is None or response.status >= 400:
                status = response.status if response else "no response"
                issues.append(f"Blocked or failed page load: HTTP {status} for {target_url}")
                executed_steps.append(_step("navigate", target_url, "failed", f"HTTP {status}"))
                browser.close()
                error_type = "ACCESS_BLOCKED" if response is not None else "SOURCE_UNAVAILABLE"
                return BrowserRunResult(
                    success=False, source_url=target_url, issues=issues,
                    executed_steps=executed_steps, error_type=error_type,
                )
            executed_steps.append(_step("navigate", target_url, "ok", f"HTTP {response.status}"))

            try:
                page.wait_for_selector(wait_selector, timeout=8000)
                executed_steps.append(_step("wait_for_selector", wait_selector, "ok"))
            except PlaywrightTimeoutError:
                issues.append(f"Timed out waiting for {wait_selector} - page layout may have changed.")
                executed_steps.append(_step("wait_for_selector", wait_selector, "failed", "timeout after 8000ms"))
                browser.close()
                return BrowserRunResult(
                    success=False, source_url=target_url, issues=issues,
                    executed_steps=executed_steps, error_type="SELECTOR_NOT_FOUND",
                )

            page_title = page.title()
            html_excerpt = page.inner_html("body")
            screenshot_bytes = page.screenshot(full_page=True)
            executed_steps.append(_step("capture", target_url, "ok", f"title='{page_title}'"))
            captured_at = datetime.now(timezone.utc).isoformat()
        except PlaywrightTimeoutError:
            issues.append(f"Timed out navigating to {target_url}.")
            executed_steps.append(_step("navigate", target_url, "failed", "timeout"))
            browser.close()
            return BrowserRunResult(
                success=False, source_url=target_url, issues=issues,
                executed_steps=executed_steps, error_type="TIMEOUT",
            )
        except Exception as exc:
            issues.append(f"Unexpected browser error: {exc}")
            executed_steps.append(_step("unknown", target_url, "failed", str(exc)[:200]))
            browser.close()
            return BrowserRunResult(
                success=False, source_url=target_url, issues=issues,
                executed_steps=executed_steps, error_type="UNKNOWN",
            )
        browser.close()

    return BrowserRunResult(
        success=True, html_excerpt=html_excerpt, screenshot_bytes=screenshot_bytes,
        source_url=target_url, page_title=page_title, captured_at=captured_at,
        issues=issues, executed_steps=executed_steps, error_type=None,
    )
