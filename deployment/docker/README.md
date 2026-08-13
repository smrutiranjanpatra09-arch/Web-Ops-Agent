# Docker

The build files live at the repository root (Docker requires the build context
to include the app source, and keeping them at the root is the conventional
layout that `docker compose up` finds with no extra flags):

- [`../../Dockerfile`](../../Dockerfile): single image for all four services
- [`../../docker-compose.yml`](../../docker-compose.yml): service definitions
- [`../../.dockerignore`](../../.dockerignore): keeps venv, `.env`, DB, and screenshots out of the image

## Quick start

```bash
docker compose up --build            # dashboard, API, mock site
docker compose --profile recurring up --build   # ...plus the scheduler
```

| Service | Port | Purpose |
| --- | --- | --- |
| `mock-site` | 5050 | The only site the agent is allowed to browse |
| `api` | 8000 | FastAPI job-orchestration API (`/docs` for Swagger) |
| `dashboard` | 8501 | Streamlit operations dashboard |
| `scheduler` | n/a | Recurring runs every 300s (opt-in profile) |

## Design notes

**One image, four commands.** All services share the same codebase, so building
four separate images would only duplicate a ~2GB Playwright layer. The compose
file varies `command` instead.

**Playwright base image.** Chromium needs a long list of system libraries
(`libnss3`, `libatk`, `libgbm`, fonts, etc.). Installing them manually on
`python:slim` is brittle, so this uses
`mcr.microsoft.com/playwright/python:v1.47.0-jammy`, which ships them and
pins to the same Playwright version as `requirements.txt`.

**Shared volume.** `agent-data` is mounted into every service at `/app/data`, so
the API, dashboard, and scheduler all read and write the same SQLite database
and screenshot directory. Without this, each container would keep its own run
history and the comparison step would never find a prior snapshot.

**Healthcheck gating.** `api`, `dashboard`, and `scheduler` all
`depends_on: mock-site: condition: service_healthy`, so nothing tries to browse
before the target site is actually serving.

## Resetting

```bash
docker compose down          # stop, keep run history
docker compose down -v       # stop and wipe the database + screenshots
```
