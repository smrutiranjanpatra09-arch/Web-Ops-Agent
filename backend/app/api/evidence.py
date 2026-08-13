from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from backend.app.database.object_storage import get_object_bytes

router = APIRouter(prefix="/api/evidence", tags=["evidence"])


@router.get("/{object_key:path}")
def get_evidence_object(object_key: str):
    # streams an evidence artifact (screenshot/HTML) through the API rather
    # than handing out a MinIO URL directly - sidesteps presigned-URL Host
    # header binding issues across container/host network boundaries, and
    # keeps the bucket private (no public MinIO exposure needed)
    try:
        data, content_type = get_object_bytes(object_key)
    except Exception:
        raise HTTPException(404, f"Evidence object '{object_key}' not found.")
    return Response(content=data, media_type=content_type)
