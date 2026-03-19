from __future__ import annotations

import logging
from typing import Any

from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient

from api.common.config import get_api_settings

logger = logging.getLogger(__name__)

_client: SearchClient | None = None


def _get_client() -> SearchClient:
    global _client
    if _client is None:
        s = get_api_settings()
        _client = SearchClient(
            endpoint=s.SEARCH_ENDPOINT,
            index_name=s.SEARCH_INDEX,
            credential=DefaultAzureCredential(),
        )
    return _client


def search_invoices(
    query: str,
    top: int = 10,
    filters: str | None = None,
) -> list[dict[str, Any]]:
    client = _get_client()
    results = client.search(
        search_text=query,
        top=top,
        filter=filters,
        include_total_count=True,
    )
    docs = []
    for r in results:
        docs.append({
            "id": r.get("id"),
            "invoice_id": r.get("invoice_id"),
            "content": r.get("content", "")[:500],
            "vendor_name": r.get("vendor_name"),
            "invoice_number": r.get("invoice_number"),
            "spend_category": r.get("spend_category"),
            "score": r.get("@search.score"),
        })
    return docs
