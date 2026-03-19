"""Invoice CRUD + search tools for the SpendAnalyzer agent."""
from __future__ import annotations

import json
from typing import Annotated

from agent_framework import tool

from api.adapters import cosmos_adapter, search_adapter


@tool
def search_invoices(
    query: Annotated[str, "Natural-language search query, e.g. 'office supplies from Staples'"],
    top: Annotated[int, "Maximum number of results to return"] = 10,
) -> str:
    """Search invoices using AI Search. Use when the user asks to find invoices by content, vendor, or category."""
    results = search_adapter.search_invoices(query=query, top=top)
    return json.dumps(results, default=str)


@tool
def list_invoices(
    user_id: Annotated[str, "The user's OID (object ID)"],
    offset: Annotated[int, "Number of records to skip"] = 0,
    limit: Annotated[int, "Max records to return"] = 20,
) -> str:
    """List the user's invoices ordered by most recent. Use for browsing or paginating invoices."""
    results = cosmos_adapter.list_invoices(user_id=user_id, offset=offset, limit=limit)
    summary = [
        {
            "id": r["id"],
            "vendor": r.get("vendor_name"),
            "amount": r.get("total_amount"),
            "category": r.get("spend_category"),
            "date": r.get("invoice_date"),
            "status": r.get("status"),
        }
        for r in results
    ]
    return json.dumps(summary, default=str)


@tool
def get_invoice_detail(
    invoice_id: Annotated[str, "The invoice ID to retrieve"],
    user_id: Annotated[str, "The user's OID"],
) -> str:
    """Get full details for a single invoice. Use when the user asks about a specific invoice."""
    record = cosmos_adapter.get_invoice(invoice_id, user_id)
    if not record:
        return json.dumps({"error": "Invoice not found"})
    exclude = {"_rid", "_self", "_etag", "_attachments", "_ts"}
    return json.dumps({k: v for k, v in record.items() if k not in exclude}, default=str)


@tool
def update_invoice(
    invoice_id: Annotated[str, "The invoice ID to update"],
    user_id: Annotated[str, "The user's OID"],
    updates: Annotated[str, "JSON string of fields to update, e.g. '{\"notes\":\"reviewed\"}'"],
) -> str:
    """Update specific fields on an invoice. ALWAYS confirm with the user before calling."""
    import json as _json
    update_dict = _json.loads(updates)
    protected = {"id", "user_id", "blob_path", "correlation_id"}
    update_dict = {k: v for k, v in update_dict.items() if k not in protected}

    result = cosmos_adapter.update_invoice(invoice_id, user_id, update_dict)
    if not result:
        return json.dumps({"error": "Invoice not found or update failed"})
    return json.dumps({"success": True, "updated_fields": list(update_dict.keys())})


@tool
def delete_invoice(
    invoice_id: Annotated[str, "The invoice ID to delete"],
    user_id: Annotated[str, "The user's OID"],
) -> str:
    """Delete an invoice. ALWAYS confirm with the user before calling."""
    success = cosmos_adapter.delete_invoice(invoice_id, user_id)
    return json.dumps({"success": success})
