from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.auth import router as auth_router
from backend.app.api.chat import router as chat_router
from backend.app.api.changes import router as changes_router
from backend.app.api.evidence import router as evidence_router
from backend.app.api.failures import router as failures_router
from backend.app.api.health import router as health_router
from backend.app.api.model_calls import router as model_calls_router
from backend.app.api.plans import router as plans_router
from backend.app.api.reviews import router as reviews_router
from backend.app.api.runs import router as runs_router
from backend.app.api.schedules import router as schedules_router
from backend.app.api.signals import router as signals_router
from backend.app.api.sources import router as sources_router
from backend.app.api.tasks import router as tasks_router
from backend.app.api.templates import router as templates_router
from backend.app.core.config import get_settings
from backend.app.database.object_storage import ensure_bucket

app = FastAPI(
    title="MakeMyTrip Autonomous Web Operations Agent API",
    version="0.1.0",
)

# frontend runs on a different origin (Vite dev server / a separate frontend
# container) - without this, every fetch from the browser fails CORS even
# though curl/server-to-server calls work fine. Origins are an explicit
# allowlist (CORS_ALLOWED_ORIGINS env var), never a wildcard - the API issues
# bearer tokens for authenticated actions, and allow_origins=["*"] combined
# with credentialed requests is exactly the misconfiguration CORS exists to
# prevent.
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(tasks_router)
app.include_router(runs_router)
app.include_router(plans_router)
app.include_router(reviews_router)
app.include_router(signals_router)
app.include_router(templates_router)
app.include_router(schedules_router)
app.include_router(evidence_router)
app.include_router(sources_router)
app.include_router(failures_router)
app.include_router(model_calls_router)
app.include_router(changes_router)
app.include_router(chat_router)


@app.on_event("startup")
def on_startup():
    ensure_bucket()
