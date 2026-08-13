# Demonstration Flow

A step-by-step walkthrough from a clean clone to a completed run with full
evidence traceability.

## 1. Start the infrastructure

```bash
cp .env.example .env
# fill in GEMINI_API_KEY if you have one - the pipeline works end-to-end
# without it (deterministic fallbacks for planning/summaries), but a real
# key lets you see genuine AI-generated plans and business-impact narratives

docker compose up -d postgres redis minio mock-site
```

Wait for all four to report healthy: `docker compose ps`.

## 2. Run migrations (first time only)

```bash
docker compose up -d api
docker compose exec api python -m alembic -c backend/alembic.ini upgrade head
```

Confirm: `docker compose exec postgres psql -U webops -d webops -c "\dt"` should
list 21 tables.

## 3. Start the workers and frontend

```bash
docker compose up -d worker browser-worker frontend
```

Open **http://localhost:5173**.

## 4. Register an approved source (required before any browsing)

The browser worker refuses to navigate to a domain that isn't registered.
Seed one for the mock site:

```bash
docker compose exec postgres psql -U webops -d webops -c "
INSERT INTO sources (id, domain, category, owner, access_type, auth_required,
                      review_required, health_state, consecutive_failures,
                      total_runs, total_failures, created_at, updated_at)
VALUES ('src-demo', 'mock-site:5050', 'hotel_pricing_watch', 'Growth',
        'public', false, false, 'HEALTHY', 0, 0, 0, now(), now());

INSERT INTO source_policies (id, source_id, url_pattern, allowed_actions,
                              rate_limit_per_minute, timeout_seconds,
                              retry_cap, created_at, updated_at)
VALUES
  ('pol-hotels', 'src-demo', 'http://mock-site:5050/hotels/', 'navigate,extract,screenshot', 10, 15, 2, now(), now()),
  ('pol-campaign', 'src-demo', 'http://mock-site:5050/campaign/', 'navigate,extract,screenshot', 10, 15, 2, now(), now()),
  ('pol-competitor', 'src-demo', 'http://mock-site:5050/competitor/', 'navigate,extract,screenshot', 10, 15, 2, now(), now()),
  ('pol-partner', 'src-demo', 'http://mock-site:5050/partner/', 'navigate,extract,screenshot', 10, 15, 2, now(), now()),
  ('pol-trends', 'src-demo', 'http://mock-site:5050/trends', 'navigate,extract,screenshot', 10, 15, 2, now(), now());
"
```

## 5. Create a task and watch it run

**Through the UI:** go to Task Intake, pick "Hotel Pricing Watch", entity
`Goa`, target URL `http://mock-site:5050/hotels/Goa`, submit. You're taken to
the run detail page, which polls live and shows the journey stepper advancing
through each stage as the real pipeline executes.

**Through the API:**

```bash
TASK_ID=$(curl -s -X POST http://localhost:8000/api/tasks -H "Content-Type: application/json" -d '{
  "objective": "Track hotel pricing for Goa",
  "workflow_type": "hotel_pricing_watch",
  "entity_key": "Goa",
  "target_url": "http://mock-site:5050/hotels/Goa"
}' | python -c "import sys,json; print(json.load(sys.stdin)['id'])")

RUN_ID=$(curl -s -X POST http://localhost:8000/api/runs -H "Content-Type: application/json" -d "{\"task_id\": \"$TASK_ID\"}" | python -c "import sys,json; print(json.load(sys.stdin)['id'])")

# poll until terminal
curl -s http://localhost:8000/api/runs/$RUN_ID | python -m json.tool
```

## 6. Inspect the real evidence chain

```bash
curl -s http://localhost:8000/api/runs/$RUN_ID/evidence | python -m json.tool
```

Note the `screenshot_object_key`/`html_object_key` and `screenshot_url`. Open
`http://localhost:8000/api/evidence/screenshots/{run_id}.png` in a browser.
That's a real, full-page Chromium screenshot of the exact page the agent
navigated, proxied out of MinIO.

```bash
curl -s http://localhost:8000/api/runs/$RUN_ID/results | python -m json.tool
```

Shows the real extracted snapshot fields, the deterministic comparison
result, and (on the second run for the same entity) a genuine comparison
against the prior snapshot rather than everything reporting as new.

## 7. Trigger a review, if one comes up

Runs with significant/low-confidence findings land at `REVIEW_REQUIRED`. Go
to the Human Review page, or:

```bash
curl -s http://localhost:8000/api/reviews?status=pending | python -m json.tool
curl -s -X POST http://localhost:8000/api/reviews/{review_id}/decision \
  -H "Content-Type: application/json" -d '{"action": "approve", "reason": "looks right"}'
```

## 8. Turn on real recurring scheduling (optional)

```bash
docker compose up -d scheduler
```

Create a template + schedule via `POST /api/templates` and `POST
/api/schedules` (see `docs/api_reference.md`), then watch, with no further
action, the scheduler's own 60-second tick discover the due schedule and
create a real run entirely unattended. Verified live during this build: a
schedule created with no prior `last_run_at` was picked up and triggered by
the real running scheduler container within one tick, no manual intervention.

## 9. What "real" means here

Every claim above is independently checkable, not asserted:

- `docker compose logs browser-worker` shows real Chromium navigation lines
  with real page titles
- The screenshot at `/api/evidence/{key}` is a genuine PNG (check the file
  size: real full-page captures are tens to hundreds of KB, never a few
  bytes)
- `docker compose logs worker | grep "structured call completed"` shows
  real Gemini/Ollama calls, when the LLM path is live
- `tests/test_integration.py::test_run_evidence_is_real_playwright_output_not_fabricated`
  is an automated version of the screenshot check above. It asserts the PNG
  magic bytes and a minimum real file size
