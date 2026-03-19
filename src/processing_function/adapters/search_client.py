from __future__ import annotations

import logging
from typing import Any

from azure.search.documents import SearchClient as AzureSearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
    SearchableField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SearchFieldDataType as DT,
)

from src.common.auth.credentials import get_credential
from src.common.config.settings import get_settings

logger = logging.getLogger(__name__)

EMBEDDING_DIMENSIONS = 3072


class SearchAdapter:
    def __init__(self) -> None:
        s = get_settings()
        cred = get_credential()
        self._client = AzureSearchClient(
            endpoint=s.SEARCH_ENDPOINT,
            index_name=s.SEARCH_INDEX,
            credential=cred,
        )
        self._use_embeddings = s.SEARCH_USE_EMBEDDINGS

    def upload_documents(self, docs: list[dict[str, Any]]) -> None:
        if not docs:
            return
        self._client.upload_documents(documents=docs)
        logger.info("Indexed %d documents to search", len(docs))

    def build_search_document(
        self,
        invoice_id: str,
        chunk_id: int,
        content: str,
        metadata: dict[str, Any],
        embedding: list[float] | None = None,
    ) -> dict[str, Any]:
        doc: dict[str, Any] = {
            "id": f"{invoice_id}:{chunk_id}",
            "invoice_id": invoice_id,
            "chunk_id": str(chunk_id),
            "content": content,
            "vendor_name": metadata.get("vendor_name", ""),
            "invoice_number": metadata.get("invoice_number", ""),
            "spend_category": metadata.get("spend_category", ""),
            "invoice_date": metadata.get("invoice_date", ""),
            "total_amount": metadata.get("total_amount"),
            "user_id": metadata.get("user_id", ""),
        }
        if self._use_embeddings and embedding:
            doc["content_vector"] = embedding
        return doc
