from fastapi import APIRouter
from redis import Redis
from sqlalchemy import text

from backend.app.core.config import get_settings
from backend.app.database.object_storage import get_minio_client
from backend.app.database.session import engine

router = APIRouter()


@router.get("/api/health")
def health():
    settings = get_settings()
    checks = {"postgres": "unknown", "redis": "unknown", "minio": "unknown"}

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["postgres"] = "healthy"
    except Exception as exc:
        checks["postgres"] = f"unhealthy: {exc}"

    try:
        Redis.from_url(settings.redis_url).ping()
        checks["redis"] = "healthy"
    except Exception as exc:
        checks["redis"] = f"unhealthy: {exc}"

    try:
        get_minio_client().list_buckets()
        checks["minio"] = "healthy"
    except Exception as exc:
        checks["minio"] = f"unhealthy: {exc}"

    overall = "ok" if all(v == "healthy" for v in checks.values()) else "degraded"
    return {"status": overall, "services": checks}
