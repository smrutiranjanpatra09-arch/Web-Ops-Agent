from functools import lru_cache

from minio import Minio

from backend.app.core.config import get_settings


@lru_cache
def get_minio_client() -> Minio:
    settings = get_settings()
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=settings.minio_secure,
    )


def ensure_bucket() -> None:
    settings = get_settings()
    client = get_minio_client()
    if not client.bucket_exists(settings.minio_bucket):
        client.make_bucket(settings.minio_bucket)


def delete_object(object_key: str) -> None:
    # used by the retention job (backend/app/services/retention_service.py) to
    # purge raw artifact bytes once they age past RETENTION_DAYS_RAW_ARTIFACTS.
    # The caller is responsible for keeping the Evidence row itself and only
    # clearing its object-key columns - this function only ever touches MinIO.
    settings = get_settings()
    client = get_minio_client()
    client.remove_object(settings.minio_bucket, object_key)


def get_object_bytes(object_key: str) -> tuple[bytes, str]:
    # evidence stays in a private bucket - the API streams bytes through
    # itself rather than handing out a presigned URL. Presigned URLs bind
    # the signature to the exact Host header used at signing time, which
    # breaks the moment the signing host (container-internal) differs from
    # the host a browser can reach (localhost:9000 via the published port) -
    # proxying through the API sidesteps that mismatch entirely.
    settings = get_settings()
    client = get_minio_client()
    response = client.get_object(settings.minio_bucket, object_key)
    try:
        data = response.read()
        content_type = response.headers.get("Content-Type", "application/octet-stream")
        return data, content_type
    finally:
        response.close()
        response.release_conn()
