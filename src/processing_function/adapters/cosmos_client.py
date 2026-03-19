from __future__ import annotations

import logging
from typing import Any

from azure.cosmos import CosmosClient, PartitionKey

from src.common.auth.credentials import get_credential
from src.common.config.settings import get_settings

logger = logging.getLogger(__name__)


class CosmosAdapter:
    def __init__(self) -> None:
        s = get_settings()
        self._client = CosmosClient(url=s.COSMOS_ENDPOINT, credential=get_credential())
        db = self._client.get_database_client(s.COSMOS_DATABASE_NAME)
        self._invoices = db.get_container_client(s.COSMOS_INVOICES_CONTAINER)

    def upsert_invoice(self, record: dict[str, Any]) -> None:
        self._invoices.upsert_item(body=record)
        logger.info("Upserted invoice %s", record.get("id"))

    def get_invoice(self, invoice_id: str, user_id: str) -> dict[str, Any] | None:
        try:
            return self._invoices.read_item(item=invoice_id, partition_key=user_id)
        except Exception:
            return None

    def query_recent_invoices(
        self,
        vendor_name: str,
        total_amount: float | None,
        invoice_date: str,
        limit: int = 5,
    ) -> list[dict]:
        conditions = ["c.vendor_name = @vendor"]
        params: list[dict] = [{"name": "@vendor", "value": vendor_name}]

        if total_amount is not None:
            conditions.append("c.total_amount = @amount")
            params.append({"name": "@amount", "value": total_amount})
        if invoice_date:
            conditions.append("c.invoice_date = @date")
            params.append({"name": "@date", "value": invoice_date})

        query = f"SELECT TOP {limit} c.id, c.invoice_number, c.total_amount, c.invoice_date FROM c WHERE {' AND '.join(conditions)}"

        return list(self._invoices.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=True,
        ))
