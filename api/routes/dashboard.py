"""Dashboard summary endpoint."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from api.auth.token_validator import get_current_user
from api.adapters import cosmos_adapter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
async def get_dashboard(user: dict = Depends(get_current_user)):
    user_id = user["oid"]

    total_q = "SELECT VALUE COUNT(1) FROM c WHERE c.user_id = @uid AND c.status = 'processed'"
    total_params = [{"name": "@uid", "value": user_id}]

    spend_q = "SELECT VALUE SUM(c.total_amount) FROM c WHERE c.user_id = @uid AND c.status = 'processed'"

    category_q = (
        "SELECT c.spend_category AS label, COUNT(1) AS count, SUM(c.total_amount) AS total "
        "FROM c WHERE c.user_id = @uid AND c.status = 'processed' "
        "GROUP BY c.spend_category"
    )

    recent_q = (
        "SELECT c.id, c.vendor_name, c.total_amount, c.spend_category, c.invoice_date, c.status "
        "FROM c WHERE c.user_id = @uid ORDER BY c.processed_at DESC OFFSET 0 LIMIT 10"
    )

    anomaly_q = (
        "SELECT VALUE COUNT(1) FROM c "
        "WHERE c.user_id = @uid AND ARRAY_LENGTH(c.anomaly_flags) > 0"
    )

    total_result = cosmos_adapter.query_invoices(total_q, total_params)
    spend_result = cosmos_adapter.query_invoices(spend_q, total_params)
    categories = cosmos_adapter.query_invoices(category_q, total_params)
    recent = cosmos_adapter.query_invoices(recent_q, total_params)
    anomalies = cosmos_adapter.query_invoices(anomaly_q, total_params)

    return {
        "total_invoices": total_result[0] if total_result else 0,
        "total_spend": spend_result[0] if spend_result else 0,
        "anomaly_count": anomalies[0] if anomalies else 0,
        "by_category": categories,
        "recent_invoices": recent,
    }
