"""Invoice upload endpoint."""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException

from api.auth.token_validator import get_current_user
from api.adapters.blob_adapter import upload_blob
from api.common.config import get_api_settings

logger = logging.getLogger(__name__)

ALLOWED_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/tiff",
}

router = APIRouter(prefix="/api/upload", tags=["upload"])


@router.post("")
async def upload_invoice(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")

    user_id = user["oid"]
    upload_id = str(uuid.uuid4())
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "bin"
    blob_path = f"{user_id}/{upload_id}/{file.filename}"

    content = await file.read()
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 25 MB)")

    s = get_api_settings()
    url = upload_blob(s.UPLOADS_CONTAINER_NAME, blob_path, content, file.content_type)

    logger.info("Uploaded invoice: user=%s, blob=%s, size=%d", user_id, blob_path, len(content))

    return {
        "upload_id": upload_id,
        "blob_path": blob_path,
        "filename": file.filename,
        "size_bytes": len(content),
        "content_type": file.content_type,
    }
