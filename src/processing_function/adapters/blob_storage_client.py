from __future__ import annotations

import logging

from azure.storage.blob import BlobServiceClient

from src.common.auth.credentials import get_credential
from src.common.config.settings import get_settings

logger = logging.getLogger(__name__)


class BlobStorageAdapter:
    def __init__(self) -> None:
        s = get_settings()
        self._client = BlobServiceClient(
            account_url=f"https://{s.STORAGE_ACCOUNT_NAME}.blob.core.windows.net",
            credential=get_credential(),
        )

    def download_blob(self, container: str, blob_path: str) -> bytes:
        blob = self._client.get_blob_client(container, blob_path)
        return blob.download_blob().readall()

    def get_blob_properties(self, container: str, blob_path: str) -> dict:
        blob = self._client.get_blob_client(container, blob_path)
        props = blob.get_blob_properties()
        return {
            "name": props.name,
            "size": props.size,
            "content_type": props.content_settings.content_type,
            "etag": props.etag,
        }
