"""Invoice REST endpoints."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.auth.token_validator import get_current_user
from api.adapters import cosmos_adapter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


class InvoiceUpdate(BaseModel):
    notes: str | None = None
    tags: list[str] | None = None
    spend_category: str | None = None
    subcategory: str | None = None


@router.get("")
async def list_invoices(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(get_current_user),
):
    return cosmos_adapter.list_invoices(user["oid"], offset=offset, limit=limit)


@router.get("/{invoice_id}")
async def get_invoice(invoice_id: str, user: dict = Depends(get_current_user)):
    record = cosmos_adapter.get_invoice(invoice_id, user["oid"])
    if not record:
        raise HTTPException(status_code=404, detail="Invoice not found")
    exclude = {"_rid", "_self", "_etag", "_attachments", "_ts"}
    return {k: v for k, v in record.items() if k not in exclude}


@router.patch("/{invoice_id}")
async def update_invoice(
    invoice_id: str,
    body: InvoiceUpdate,
    user: dict = Depends(get_current_user),
):
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = cosmos_adapter.update_invoice(invoice_id, user["oid"], updates)
    if not result:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return {"updated": True, "fields": list(updates.keys())}


@router.delete("/{invoice_id}")
async def delete_invoice(invoice_id: str, user: dict = Depends(get_current_user)):
    success = cosmos_adapter.delete_invoice(invoice_id, user["oid"])
    if not success:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return {"deleted": True}
