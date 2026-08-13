# Browser Policy

## Domain allowlist (source registry)

No browser action may target a domain not present in the `Source` table.
`browser/policies/allowlist.py`'s `check_domain_allowed()` looks up the
target URL's domain and rejects with `POLICY_RESTRICTED` if it isn't
registered, before any real navigation happens. This runs on **every** entry
point into the browser, including the self-healing recovery loop
(`intelligence/source_health/recovery.py`), which re-dispatches through the
same queue rather than calling Playwright directly.

Each registered `Source` also has one or more `SourcePolicy` rows scoping
exactly which URL patterns under that domain are approved
(`resolve_policy()`), with per-pattern rate limits, timeouts, and retry caps.

```sql
INSERT INTO sources (id, domain, category, owner, access_type, auth_required,
                      review_required, health_state, consecutive_failures,
                      total_runs, total_failures, created_at, updated_at)
VALUES ('src-1', 'mock-site:5050', 'hotel_pricing_watch', 'Growth', 'public',
        false, false, 'HEALTHY', 0, 0, 0, now(), now());

INSERT INTO source_policies (id, source_id, url_pattern, allowed_actions,
                              rate_limit_per_minute, timeout_seconds,
                              retry_cap, created_at, updated_at)
VALUES ('pol-1', 'src-1', 'http://mock-site:5050/hotels/',
        'navigate,extract,screenshot', 10, 15, 2, now(), now());
```

## Why a mock site instead of a real travel site

`mock_site/` is a small Flask app we fully control, acting as an approved
source: real HTML, real branding, real per-workflow pages, generated
deterministically (seeded random) so runs are reproducible. Real travel
sites' ToS typically prohibit automated scraping, and their anti-bot defenses
(fingerprinting, rate limiting, CAPTCHAs) are exactly the kind of thing this
system's controlled-autonomy design is meant to respect, not fight around.
The `Source`/`SourcePolicy` model is domain-agnostic. Pointing it at a real
approved partner feed instead is a data change, not an architecture change.

## Rate limits, timeouts, retries

Each `SourcePolicy` row carries `rate_limit_per_minute`, `timeout_seconds`,
and `retry_cap`. `browser/actions/navigate.py` enforces the per-navigation
timeout; retry policy is type-specific per the error taxonomy (below). A
`SELECTOR_NOT_FOUND` triggers bounded self-healing recovery (max 2 candidate
selectors, each independently validated by a real re-navigation), while
`POLICY_RESTRICTED` and `LOGIN_REQUIRED` never auto-retry.

## Credential handling

No secret ever reaches the browser layer, the frontend, or logs.
`GEMINI_API_KEY`/`OLLAMA_BASE_URL` are read server-side from `.env` and used
only for planning/summary text generation, never passed to or read by the
browser worker. `agents/llm.py`'s Gemini calls put the key in a request
header, not a URL, so it can't leak into tracebacks or proxy logs. Confirmed
via a structured 8-point security audit (see `BUILD_STATE.md` §23) that no
hardcoded secret exists anywhere in source, and the frontend never references
any key beyond the non-secret API base URL.

## Failure visibility (error taxonomy)

Every browser failure surfaces as one of these types, recorded on the `Run`
and (where applicable) a `Failure` row, never silently swallowed:
`SOURCE_UNAVAILABLE`, `PAGE_CHANGED`, `SELECTOR_NOT_FOUND`, `TIMEOUT`,
`LOGIN_REQUIRED`, `ACCESS_BLOCKED`, `POPUP_BLOCKED`, `EXTRACTION_FAILED`,
`VALIDATION_FAILED`, `MODEL_OUTPUT_INVALID`, `POLICY_RESTRICTED`,
`STORAGE_FAILED`, `QUEUE_FAILED`, `UNKNOWN`.

## Evidence capture

Every successful browse step uploads a real full-page screenshot and the
captured HTML to MinIO (private bucket), with metadata (`source_url`,
`page_title`, `captured_at`, object keys, confidence) persisted to the
`Evidence` table in Postgres. The frontend fetches screenshots through
`GET /api/evidence/{key}`, which proxies bytes through the API rather than a
presigned URL (see `docs/architecture.md`'s storage-model section for why).

## Sensitive workflow gate

Any `Task` created with `review_required=true` pauses the run at
`AWAITING_APPROVAL` after planning, before any browsing happens. A human
sees the exact plan (target URL, steps) via `GET /api/runs/{id}` and can
`POST /api/runs/{id}/approve` or `/reject`. Rejection marks the run `CANCELLED`
with the browser never invoked.

## Prompt injection defense

Scraped page content is treated as untrusted data, never as instructions.
`agents/planner.py` and `agents/completion.py` build LLM prompts exclusively
from structured, already-deterministic fields (objective, entity key, target
URL, comparison result values). Raw HTML/extracted text never flows into an
LLM prompt anywhere in the pipeline. Confirmed via the security audit in
`BUILD_STATE.md` §23.
