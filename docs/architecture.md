# Architecture

## Pipeline

```
Task Intake (React UI / REST API)
   -> Validate + persist + enqueue        FastAPI handler - never runs the
                                            browser/LLM inline (engineering guidelines, §9)
   -> Planning                             Gemini (or Ollama, or a deterministic
                                            fallback) writes a browsing plan
   -> [optional] Approval gate             sensitive workflows pause here
   -> Browser execution                    dispatched to a SEPARATE Redis queue,
                                            picked up by the browser-worker
                                            container (the only place
                                            Playwright/Chromium runs)
   -> Evidence capture                     screenshot + HTML to MinIO,
                                            metadata to Postgres
   -> Extraction                           BeautifulSoup, deterministic,
                                            workflow-specific parser
   -> Snapshot                             normalized SnapshotField rows,
                                            not a JSON blob
   -> Deterministic comparison             abs-diff + %-diff in code, never
                                            via LLM
   -> Significance + noise classification  <1%/1-5%/5-15%/>15% buckets
   -> Reasoning                            Gemini (or Ollama) writes the
                                            business-impact summary, grounded
                                            in the deterministic comparison
                                            results, never recomputes them
   -> Signal + Review (if triggered)       real Signal/Review rows
   -> Completion
```

Every run is persisted as a `Run` row moving through a 21-state machine
(`backend/app/models/run.py`, enforced by `backend/app/services/state_machine.py`):
`CREATED → VALIDATING → PLANNING → PLAN_READY → AWAITING_APPROVAL → APPROVED →
QUEUED → BROWSER_STARTING → BROWSING → EXTRACTION → VALIDATING_DATA →
SNAPSHOTTING → COMPARING → REASONING → REVIEW_REQUIRED → COMPLETING →
COMPLETED`, plus branch states `RECOVERY`, `RERUN_REQUESTED`, `FAILED`,
`CANCELLED` reachable from most active states. Every transition is logged to
`RunStep` (previous state, new state, actor, reason, timestamp) and mirrored
to `AuditEvent`.

## Why the browser runs in its own container, on its own queue

Playwright/Chromium must never run inside the FastAPI process or the generic
worker (engineering guidelines, §10). This isn't just a rule, it's enforced by
infrastructure: `browser-worker`'s Docker image is built from
`mcr.microsoft.com/playwright/python`, and it's the *only* image with
Playwright installed. The generic `worker` container's image
(`Dockerfile.backend`) never installs it.

That means the generic worker can't call `browser_tools.navigate()` directly.
It would raise `ModuleNotFoundError: No module named 'playwright'`. Instead,
`backend/app/services/orchestrator.py`'s `browse_node` enqueues a job onto a
**second** Redis queue (`browser`, distinct from the `runs` queue the generic
worker listens on) and polls for the result:

```python
job_id = enqueue_browse(state["run_id"], state["target_url"], wait_selector)
job = get_browser_queue().fetch_job(job_id)
# ...poll job.get_status() until finished/failed...
```

`browser/worker.py` is the RQ worker that actually executes `browse_job()`
inside the browser-worker container, where Playwright genuinely exists. This
queue split was discovered as a real bug during live testing (Phase 7): the
first version called browser tools in-process and crashed with exactly that
`ModuleNotFoundError` the moment it ran inside the real container, not just
locally where both packages happened to be installed.

Recovery (self-healing selectors, see below) hits the same issue and uses the
same fix: `intelligence/source_health/recovery.py`'s `attempt_selector_recovery`
dispatches each candidate selector through `enqueue_browse`, never calling
Playwright in-process.

## Why LangGraph

`backend/app/services/orchestrator.py` wires the pipeline stages together as
nodes in a real LangGraph `StateGraph`: `plan → approval_gate → browse →
extract → snapshot → compare → reason`. Each node:

1. Transitions the `Run`'s real state machine
2. Calls into an MCP tool (never a subsystem directly)
3. Returns a state update LangGraph merges into the graph's shared state

The entry point is conditional (`set_conditional_entry_point`) so a run
resuming after human approval re-enters at `approval_gate`, skipping
re-planning, rather than restarting the whole graph from `plan`.

One quirk worth knowing if you extend this: LangGraph rejects a node that
returns an empty dict `{}`. Every node must write at least one real field.
Nodes that have nothing new to contribute return `{"run_id": state["run_id"]}`
as a harmless passthrough. This was found live (Phase 7) when several nodes
initially returned `{}` on their early-exit paths and every run silently
crashed with `InvalidUpdateError`.

## MCP tool layer

`mcp/tools/` is the only interface the orchestrator uses to touch subsystems:
`browser_tools.navigate`, `extract_tools.extract`, `snapshot_tools.*`,
`comparison_tools.compare_snapshot`, `review_tools.create_review`,
`signal_tools.create_signal`, `source_tools.check_source_health`. Every tool
returns the same `ToolResult(success, data, error_type, message)` shape,
validates its inputs, and logs its own invocation.

## Browser policy enforcement

`browser/policies/allowlist.py`'s `check_domain_allowed()` and
`resolve_policy()` run before any navigation, gated on the `Source` +
`SourcePolicy` registry in Postgres. There is exactly one code path into real
browsing (`browse_job → browser_tools.navigate → execute_browse_step`), and
every entry point, including the recovery loop, goes through it. An
unregistered domain fails with `POLICY_RESTRICTED` before Chromium ever
launches. See [`browser_policy.md`](browser_policy.md) for the full model.

## Self-healing selector recovery

When a browse step fails with `SELECTOR_NOT_FOUND`, the orchestrator
transitions the run to `RECOVERY` and calls
`intelligence/source_health/recovery.py`'s `attempt_selector_recovery()`,
which tries up to 2 candidate selectors per workflow (`CANDIDATE_SELECTORS`),
each validated by an actual re-navigation through the same browser-worker
queue, never accepting an unvalidated replacement. Every attempt is
persisted as a `RecoveryAttempt` row. If a candidate succeeds, the orchestrator
retries the browse step with the recovered selector; if all candidates fail,
the run fails normally and the source's `consecutive_failures` counter
escalates its `health_state` (`HEALTHY → DEGRADED → UNSTABLE → FAILED`).

## Storage model

PostgreSQL is the source of truth: 21 normalized tables (`backend/app/models/`),
no JSON blobs for core entities. Large artifacts (screenshots, HTML) go to
MinIO; Postgres stores only object keys. Evidence is served back to the
frontend through `GET /api/evidence/{key}`, which proxies the bytes through
the API rather than issuing a presigned MinIO URL. Presigned URLs bind their
signature to the exact `Host` header used at signing time, which breaks the
moment the signing host (container-internal `minio:9000`) differs from the
host a browser can reach (`localhost:9000`). This was a real bug found live in
Phase 12; the proxy approach sidesteps the mismatch entirely.

## Deterministic vs. AI boundary

`agents/reasoning_loop.py` computes every diff, percentage, and threshold
comparison in plain Python. The LLM is never asked to do arithmetic. Gemini
(or Ollama) is called in exactly two places: `agents/planner.py` (writing the
browsing plan) and `agents/completion.py` (writing the business-impact
narrative from already-computed comparison results). Both have a deterministic
fallback if the LLM call fails or is rate-limited, so the pipeline never stalls
waiting on an external API.

## Scheduling

`scheduler_service/main.py` runs an APScheduler `BlockingScheduler` ticking
every 60 seconds inside its own container, comparing each `Schedule`'s
`last_run_at` against its frequency interval and calling
`backend/app/services/schedule_service.py`'s `trigger_schedule()`, which
creates a real `Task` + `Run` through the exact same code path a manual
`POST /api/tasks` + `POST /api/runs` would take. No frontend timers, no
special-cased "scheduled run" logic.
