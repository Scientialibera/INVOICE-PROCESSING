from __future__ import annotations

import logging
from dataclasses import dataclass, field

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest

from src.common.auth.credentials import get_credential
from src.common.config.settings import get_settings
from src.common.models.contracts import ExtractedInvoice, LineItem
from src.common.utils.validation import safe_float

logger = logging.getLogger(__name__)


class DocIntelligenceAdapter:
    def __init__(self) -> None:
        s = get_settings()
        self._client = DocumentIntelligenceClient(
            endpoint=s.DOCINTEL_ENDPOINT,
            credential=get_credential(),
        )

    def extract_invoice(self, content: bytes) -> ExtractedInvoice:
        poller = self._client.begin_analyze_document(
            "prebuilt-invoice",
            AnalyzeDocumentRequest(bytes_source=content),
        )
        result = poller.result()

        if not result.documents:
            raw_text = result.content or ""
            return ExtractedInvoice(raw_text=raw_text, page_count=len(result.pages or []))

        doc = result.documents[0]
        fields = doc.fields or {}

        def get_str(name: str) -> str:
            f = fields.get(name)
            if not f:
                return ""
            return f.value_string or f.content or ""

        def get_currency(name: str) -> float | None:
            f = fields.get(name)
            if not f:
                return None
            if f.value_currency:
                return safe_float(f.value_currency.amount)
            return safe_float(f.content)

        def get_date(name: str) -> str:
            f = fields.get(name)
            if not f:
                return ""
            if f.value_date:
                return str(f.value_date)
            return f.content or ""

        line_items: list[LineItem] = []
        items_field = fields.get("Items")
        if items_field and items_field.value_array:
            for item in items_field.value_array:
                item_fields = item.value_object or {}
                li_get_str = lambda n: (item_fields.get(n).value_string or item_fields.get(n).content or "") if item_fields.get(n) else ""
                li_get_cur = lambda n: safe_float(item_fields[n].value_currency.amount if item_fields.get(n) and item_fields[n].value_currency else (item_fields[n].content if item_fields.get(n) else None))
                li_get_num = lambda n: safe_float(item_fields[n].value_number if item_fields.get(n) else None)

                line_items.append(LineItem(
                    description=li_get_str("Description"),
                    quantity=li_get_num("Quantity"),
                    unit_price=li_get_cur("UnitPrice"),
                    amount=li_get_cur("Amount"),
                    unit=li_get_str("Unit"),
                    product_code=li_get_str("ProductCode"),
                    tax=li_get_cur("Tax"),
                ))

        return ExtractedInvoice(
            vendor_name=get_str("VendorName"),
            vendor_address=get_str("VendorAddress"),
            customer_name=get_str("CustomerName"),
            customer_address=get_str("CustomerAddress"),
            invoice_number=get_str("InvoiceId"),
            invoice_date=get_date("InvoiceDate"),
            due_date=get_date("DueDate"),
            purchase_order=get_str("PurchaseOrder"),
            total_amount=get_currency("InvoiceTotal"),
            subtotal=get_currency("SubTotal"),
            total_tax=get_currency("TotalTax"),
            currency=get_str("CurrencyCode") or "USD",
            line_items=line_items,
            raw_text=result.content or "",
            page_count=len(result.pages or []),
            confidence=doc.confidence or 0.0,
        )
