"""Analytics tools for the SpendAnalyzer agent."""
from __future__ import annotations

import json
from typing import Annotated

from agent_framework import tool

from api.adapters import cosmos_adapter


@tool
def get_spend_summary(
    user_id: Annotated[str, "The user's OID"],
    group_by: Annotated[str, "Group by 'category', 'vendor', or 'month'"] = "category",
    start_date: Annotated[str, "Optional start date filter (YYYY-MM-DD)"] = "",
    end_date: Annotated[str, "Optional end date filter (YYYY-MM-DD)"] = "",
) -> str:
    """Aggregate spend data by category, vendor, or month. Use for dashboards and trend analysis."""
    conditions = ["c.user_id = @uid", "c.status = 'processed'"]
    params = [{"name": "@uid", "value": user_id}]

    if start_date:
        conditions.append("c.invoice_date >= @start")
        params.append({"name": "@start", "value": start_date})
    if end_date:
        conditions.append("c.invoice_date <= @end")
        params.append({"name": "@end", "value": end_date})

    where_clause = " AND ".join(conditions)

    if group_by == "vendor":
        query = f"SELECT c.vendor_name AS label, COUNT(1) AS count, SUM(c.total_amount) AS total FROM c WHERE {where_clause} GROUP BY c.vendor_name"
    elif group_by == "month":
        query = f"SELECT SUBSTRING(c.invoice_date, 0, 7) AS label, COUNT(1) AS count, SUM(c.total_amount) AS total FROM c WHERE {where_clause} GROUP BY SUBSTRING(c.invoice_date, 0, 7)"
    else:
        query = f"SELECT c.spend_category AS label, COUNT(1) AS count, SUM(c.total_amount) AS total FROM c WHERE {where_clause} GROUP BY c.spend_category"

    results = cosmos_adapter.query_invoices(query, params)
    return json.dumps(results, default=str)


@tool
def detect_anomalies(
    user_id: Annotated[str, "The user's OID"],
    limit: Annotated[int, "Max flagged invoices to return"] = 20,
) -> str:
    """Find invoices with anomaly flags. Use when the user asks about suspicious or unusual invoices."""
    query = (
        "SELECT c.id, c.vendor_name, c.total_amount, c.invoice_date, "
        "c.anomaly_flags, c.is_likely_duplicate, c.spend_category "
        "FROM c WHERE c.user_id = @uid AND ARRAY_LENGTH(c.anomaly_flags) > 0 "
        "ORDER BY c.processed_at DESC OFFSET 0 LIMIT @limit"
    )
    params = [
        {"name": "@uid", "value": user_id},
        {"name": "@limit", "value": limit},
    ]
    results = cosmos_adapter.query_invoices(query, params)
    return json.dumps(results, default=str)
