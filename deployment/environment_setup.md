# Environment Setup

## Environment variables

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `GEMINI_API_KEY` | recommended | n/a | Enables real AI planning + summaries. Free tier: https://aistudio.google.com/apikey |
| `GEMINI_MODEL_LITE` | no | `gemini-2.5-flash-lite` | Model for extraction/classification-tier calls |
| `GEMINI_MODEL` | no | `gemini-2.5-flash` | Model for planning/reasoning-tier calls |
| `OLLAMA_BASE_URL` | alternative to Gemini | n/a | Point at a local/offline Ollama server instead |
| `OLLAMA_MODEL` | no | `llama3.1` | Ollama model name |
| `LLM_PROVIDER` | no | auto-detect | Force `gemini` or `ollama`. Blank = whichever key/URL is present (Gemini wins if both) |
| `DATABASE_URL` | yes | see `.env.example` | Postgres connection string |
| `REDIS_URL` | yes | see `.env.example` | Redis connection string (queue only, never source of truth) |
| `MINIO_ENDPOINT` | yes | `localhost:9000` | Internal MinIO host:port (container-to-container) |
| `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` | yes | `webops` / `webops123` | MinIO credentials |
| `MINIO_BUCKET` | no | `evidence` | Bucket for screenshots/HTML |
| `MOCK_SITE_BASE_URL` | yes | `http://127.0.0.1:5050` | The disclosed test fixture's URL |
| `LOG_DIR` | no | `logs` | Where `agent.log` is written |

**No LLM key is required.** Without one, planning and summary generation fall
back to deterministic logic and the pipeline still completes end to end.
`GET /api/health` doesn't report the LLM provider directly, but
`agents.llm.active_provider()` does. Check the worker's logs for
`structured call completed via {provider}` to confirm the AI path is live.

## Local development (without Docker)

Playwright/Chromium only needs to be installed if you're running the
browser-worker path locally. Everything else is plain Python/FastAPI.

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements-backend.txt
pip install -r requirements-browser.txt   # only if testing browser/ locally
playwright install chromium                # only if testing browser/ locally
copy .env.example .env
# edit .env - fill in GEMINI_API_KEY, or leave blank for deterministic fallback
```

You'll also need Postgres, Redis, and MinIO running somewhere reachable
(easiest: `docker compose up -d postgres redis minio`, even if you're running
the app code itself outside Docker).

## Docker setup (recommended)

```bash
docker compose up -d postgres redis minio mock-site
docker compose up -d api
docker compose exec api python -m alembic -c backend/alembic.ini upgrade head   # first time only
docker compose up -d worker browser-worker frontend
```

| Service | URL |
| --- | --- |
| Frontend | http://localhost:5173 |
| REST API + Swagger docs | http://localhost:8000/docs |
| Mock target site | http://localhost:5050 |
| MinIO console | http://localhost:9001 |

To also run recurring scheduled jobs: `docker compose up -d scheduler`.

To start completely fresh: `docker compose down -v` (wipes Postgres/Redis/MinIO
volumes).

## Verifying the install

```bash
curl http://localhost:8000/api/health
python -m pytest tests/test_state_machine.py tests/test_significance_engine.py \
  tests/test_extraction.py tests/test_normalization.py tests/test_reasoning_loop.py \
  tests/test_campaign_and_competitor.py tests/test_partner_and_trend_extraction.py
```

91 tests total pass, including live integration tests against the running
stack. See `README.md`'s Testing section for the full command set and what
needs the stack up vs. what runs standalone.
