from __future__ import annotations

import io

from backend.app.core.config import get_settings
from backend.app.database.object_storage import get_minio_client


def upload_screenshot(run_id: str, png_bytes: bytes) -> str:
    settings = get_settings()
    client = get_minio_client()
    key = f"screenshots/{run_id}.png"
    client.put_object(settings.minio_bucket, key, io.BytesIO(png_bytes), length=len(png_bytes), content_type="image/png")
    return key


def upload_html(run_id: str, html: str) -> str:
    settings = get_settings()
    client = get_minio_client()
    data = html.encode("utf-8")
    key = f"html/{run_id}.html"
    client.put_object(settings.minio_bucket, key, io.BytesIO(data), length=len(data), content_type="text/html")
    return key
