from __future__ import annotations

import logging
from typing import Any

from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential

from api.common.config import get_api_settings

logger = logging.getLogger(__name__)

_client: CosmosClient | None = None


def _get_client() -> CosmosClient:
    global _client
    if _client is None:
        s = get_api_settings()
        _client = CosmosClient(url=s.COSMOS_ENDPOINT, credential=DefaultAzureCredential())
    return _client


def _invoices():
    s = get_api_settings()
    return _get_client().get_database_client(s.COSMOS_DATABASE_NAME).get_container_client(s.COSMOS_INVOICES_CONTAINER)


def _sessions():
    s = get_api_settings()
    return _get_client().get_database_client(s.COSMOS_DATABASE_NAME).get_container_client(s.COSMOS_SESSIONS_CONTAINER)


def list_invoices(user_id: str, offset: int = 0, limit: int = 50) -> list[dict]:
    query = "SELECT * FROM c WHERE c.user_id = @uid ORDER BY c.processed_at DESC OFFSET @offset LIMIT @limit"
    params = [
        {"name": "@uid", "value": user_id},
        {"name": "@offset", "value": offset},
        {"name": "@limit", "value": limit},
    ]
    return list(_invoices().query_items(query=query, parameters=params, enable_cross_partition_query=False))


def get_invoice(invoice_id: str, user_id: str) -> dict | None:
    try:
        return _invoices().read_item(item=invoice_id, partition_key=user_id)
    except Exception:
        return None


def update_invoice(invoice_id: str, user_id: str, updates: dict[str, Any]) -> dict | None:
    existing = get_invoice(invoice_id, user_id)
    if not existing:
        return None
    existing.update(updates)
    return _invoices().replace_item(item=invoice_id, body=existing)


def delete_invoice(invoice_id: str, user_id: str) -> bool:
    try:
        _invoices().delete_item(item=invoice_id, partition_key=user_id)
        return True
    except Exception:
        return False


def query_invoices(query: str, params: list[dict] | None = None) -> list[dict]:
    return list(_invoices().query_items(
        query=query,
        parameters=params or [],
        enable_cross_partition_query=True,
    ))


def get_or_create_session(user_id: str) -> dict:
    try:
        item = _sessions().read_item(item=user_id, partition_key=user_id)
        return item
    except Exception:
        session = {
            "id": user_id,
            "user_id": user_id,
            "thread_id": None,
        }
        _sessions().upsert_item(body=session)
        return session


def update_session(user_id: str, updates: dict[str, Any]) -> None:
    session = get_or_create_session(user_id)
    session.update(updates)
    _sessions().upsert_item(body=session)
