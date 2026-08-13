# API Reference

Base URL: `http://localhost:8000`. Interactive Swagger UI at `/docs`.

FastAPI handlers only ever validate → persist → enqueue → return. No handler
runs browser or LLM work inline (engineering guidelines, §9). Everything long-running
happens in `worker` or `browser-worker`.

## Health

- `GET /api/health`: checks Postgres, Redis, MinIO connectivity. Returns
  `{"status": "ok"|"degraded", "services": {...}}`.

## Auth

- `POST /api/auth/login`: `{email, password}`. Returns `{access_token,
  user_id, display_name, role}`. Roles: `operations_user`, `growth_user`,
  `reviewer`, `operations_owner`, `administrator`, `service_worker`. Demo
  users (one per role) are seeded via `backend/seed_users.py`; password for
  all is `#demoday26`.
- `GET /api/auth/me`: returns the current user resolved from the bearer
  token. Requires `Authorization: Bearer <token>`.
- Gated routes: `POST /api/reviews/{id}/decision` requires `reviewer`,
  `operations_owner`, or `administrator`. `POST /api/schedules` and
  `DELETE /api/schedules/{id}` require `administrator` or
  `operations_owner`. Missing/invalid token → `401`; wrong role → `403`.

## Plans

- `GET /api/plans/{id}`: returns the persisted agent plan: objective,
  status (`ready`/`approved`/`rejected`), stop conditions, risk notes, and
  the ordered browser steps. `Run.plan_id` links a run to the plan the
  orchestrator generated and persisted for it during the `PLANNING` state.

## Tasks

- `POST /api/tasks`: `{objective, workflow_type, entity_key, target_url,
  source_id?, template_id?, owner?, risk_level?, review_required?,
  completion_criteria?}`. `workflow_type` must be one of
  `hotel_pricing_watch`, `competitor_offer_tracking`, `campaign_page_monitoring`,
  `partner_update_review`, `travel_trend_scanning`.
- `GET /api/tasks`: list all tasks.
- `GET /api/tasks/{id}`: one task.

## Runs

- `POST /api/runs`: `{task_id}`. Validates the task exists, creates a `Run`
  at `VALIDATING`, enqueues it. The worker generates the real plan and stops
  at `AWAITING_APPROVAL` if the task requires review; planning is never done
  in this handler.
- `POST /api/runs/{id}/approve`: resumes a run paused at `AWAITING_APPROVAL`.
- `POST /api/runs/{id}/reject`: `{reason?}`. Marks the run `CANCELLED`; the
  browser is never invoked.
- `GET /api/runs`: list all runs.
- `GET /api/runs/{id}`: one run's current state.
- `GET /api/runs/{id}/steps`: the full state-transition history (previous
  state, new state, actor, reason, timestamp) for one run.
- `GET /api/runs/{id}/evidence`: evidence rows for one run, including
  `screenshot_url` (a relative path to `GET /api/evidence/{key}`, not a
  presigned MinIO URL).
- `GET /api/runs/{id}/results`: aggregate view: snapshots (with normalized
  fields), changes, signals, and reviews for one run in a single call.
- `POST /api/runs/{id}/rerun`: creates a brand-new run for the same task
  (the original run is left untouched for audit).

## Evidence

- `GET /api/evidence/{object_key}`: streams a screenshot or HTML artifact's
  bytes through the API from MinIO. `object_key` is a path like
  `screenshots/{run_id}.png` or `html/{run_id}.html`.

## Reviews

- `GET /api/reviews?status=pending`: list reviews, optionally filtered by
  status (`pending`, `approved`, `rejected`, `corrected`).
- `GET /api/reviews/{id}`: one review.
- `POST /api/reviews/{id}/decision`: `{action, reviewer_id?, reason?,
  corrected_value?}`. `action` is one of `approve`, `reject`, `correct`,
  `rerun`, `request_schema_change`. `rerun` additionally creates a genuine new
  `Run` for the same task. `reviewer_id` must reference a real `User` row (FK
  enforced); omit it if no user/auth system is configured yet.

## Signals

- `GET /api/signals?severity=&owner=&run_id=`: list signals, all filters
  optional.
- `GET /api/signals/{id}`: one signal.

## Templates and schedules

- `POST /api/templates`: `{name, workflow_type, path_template,
  objective_template, wait_selector, description?, expected_fields?,
  default_frequency?, owner_team?, requires_approval?, stop_conditions?}`.
- `GET /api/templates`, `GET /api/templates/{id}`.
- `POST /api/schedules`: `{template_id, workflow_type, entity_key,
  frequency, enabled?, owner_team?}`. `frequency` is one of `one_time`,
  `hourly`, `daily`, `weekly`, `campaign_driven`, `event_triggered`.
- `GET /api/schedules`: includes `last_run_id`/`last_run_at`.
- `DELETE /api/schedules/{id}`.
- `POST /api/schedules/{id}/trigger`: manually fires a schedule immediately,
  bypassing the frequency check. Creates a real task+run through the same
  path `trigger_schedule()` uses on a normal tick.

## Sources

- `GET /api/sources`: list registered sources with health state.
- `GET /api/sources/{id}/health`: one source's health detail
  (`health_state`, `consecutive_failures`, `total_runs`, `total_failures`).

## Failures

- `GET /api/failures`: recent `Failure` rows with their nested
  `RecoveryAttempt`s (candidate selector tried, result, confidence).

## Error responses

All error responses are `{"detail": "message"}` with a matching HTTP status:
`400` for validation errors (unknown workflow type, invalid frequency,
already-decided review), `404` for missing resources.
