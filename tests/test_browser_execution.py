# real Playwright execution against the real mock site - this is the specific
# proof the engineering guidelines require: acquisition genuinely comes from Chromium, not a
# stand-in. Needs the mock site running locally (python mock_site/app.py) or
# reachable at MOCK_SITE_BASE_URL, and playwright's chromium installed
# (`playwright install chromium`).
import os

import pytest

from browser.actions.navigate import navigate_and_capture

BASE_URL = os.getenv("MOCK_SITE_BASE_URL", "http://127.0.0.1:5050")


@pytest.fixture(scope="module", autouse=True)
def _ensure_mock_site():
    import requests

    try:
        requests.get(BASE_URL, timeout=3)
    except Exception:
        pytest.skip(f"mock site not reachable at {BASE_URL} - start it with `python mock_site/app.py`")


def test_valid_page_returns_real_html_and_screenshot():
    result = navigate_and_capture(f"{BASE_URL}/hotels/Goa", ".hotel-card", timeout_seconds=15)
    assert result.success is True
    assert result.error_type is None
    assert result.html_excerpt, "no HTML captured - browser never actually loaded the page"
    assert ".hotel-card" not in "".join(result.issues)

    # a real full-page screenshot of this page is never trivially small
    assert result.screenshot_bytes is not None
    assert len(result.screenshot_bytes) > 10_000
    assert result.screenshot_bytes[:8] == b"\x89PNG\r\n\x1a\n"


def test_wrong_selector_returns_visible_selector_not_found_failure():
    result = navigate_and_capture(f"{BASE_URL}/hotels/Goa", ".this-selector-does-not-exist", timeout_seconds=10)
    assert result.success is False
    assert result.error_type == "SELECTOR_NOT_FOUND"
    assert result.issues


def test_nonexistent_page_returns_visible_failure():
    result = navigate_and_capture(f"{BASE_URL}/hotels/Nowhere", ".hotel-card", timeout_seconds=10)
    assert result.success is False
    assert result.error_type in ("SELECTOR_NOT_FOUND", "ACCESS_BLOCKED")
    assert result.issues


def test_unreachable_host_returns_visible_source_unavailable_failure():
    result = navigate_and_capture("http://127.0.0.1:9/hotels/Goa", ".hotel-card", timeout_seconds=5)
    assert result.success is False
    assert result.error_type in ("SOURCE_UNAVAILABLE", "TIMEOUT")
    assert result.issues


def test_dns_resolution_failure_is_classified_as_source_unavailable_not_unknown():
    # regression test: page.goto() raising a plain playwright.sync_api.Error
    # for a DNS/connection failure (net::ERR_NAME_NOT_RESOLVED etc.) used to
    # fall into the generic `except Exception` catch-all and get classified
    # as UNKNOWN, hiding a textbook SOURCE_UNAVAILABLE case - violates
    # the engineering guidelines, section 10 ("never hide failures behind a generic error").
    # a domain that will never resolve, unlike 127.0.0.1:9 above which is a
    # connection-refused case, not a DNS failure - both must classify cleanly.
    result = navigate_and_capture(
        "http://this-domain-does-not-exist.invalid/hotels/Goa", ".hotel-card", timeout_seconds=5,
    )
    assert result.success is False
    assert result.error_type == "SOURCE_UNAVAILABLE", (
        f"expected SOURCE_UNAVAILABLE for a DNS resolution failure, got {result.error_type!r}"
    )
    assert result.issues
