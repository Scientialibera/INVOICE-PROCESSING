from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, BlobSasPermissions, generate_blob_sas, UserDelegationKey

from api.common.config import get_api_settings

logger = logging.getLogger(__name__)

_service: BlobServiceClient | None = None


def _get_service() -> BlobServiceClient:
    global _service
    if _service is None:
        s = get_api_settings()
        _service = BlobServiceClient(
            account_url=f"https://{s.STORAGE_ACCOUNT_NAME}.blob.core.windows.net",
            credential=DefaultAzureCredential(),
        )
    return _service


def upload_blob(container: str, blob_path: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    svc = _get_service()
    blob = svc.get_blob_client(container, blob_path)
    blob.upload_blob(data, overwrite=True, content_settings={"content_type": content_type})
    return blob.url


def download_blob(container: str, blob_path: str) -> bytes:
    svc = _get_service()
    return svc.get_blob_client(container, blob_path).download_blob().readall()


def download_blob_text(container: str, blob_path: str) -> str:
    return download_blob(container, blob_path).decode("utf-8")


def generate_sas_url(container: str, blob_path: str, expiry_hours: int = 1) -> str:
    s = get_api_settings()
    svc = _get_service()

    start = datetime.now(timezone.utc)
    expiry = start + timedelta(hours=expiry_hours)
    delegation_key = svc.get_user_delegation_key(
        key_start_time=start,
        key_expiry_time=expiry,
    )

    sas = generate_blob_sas(
        account_name=s.STORAGE_ACCOUNT_NAME,
        container_name=container,
        blob_name=blob_path,
        user_delegation_key=delegation_key,
        permission=BlobSasPermissions(read=True),
        expiry=expiry,
        start=start,
    )
    return f"https://{s.STORAGE_ACCOUNT_NAME}.blob.core.windows.net/{container}/{blob_path}?{sas}"
