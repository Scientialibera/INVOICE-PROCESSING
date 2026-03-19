from __future__ import annotations

import logging
from dataclasses import asdict

from src.common.models.contracts import ExtractedInvoice, Classification, ProcessedInvoice, LineItem
from src.common.utils.validation import normalize_currency
from src.processing_function.adapters.cosmos_client import CosmosAdapter

logger = logging.getLogger(__name__)


def enrich_invoice(
    extracted: ExtractedInvoice,
    classification: Classification,
    cosmos: CosmosAdapter,
    invoice_id: str,
    user_id: str,
    source: str,
    blob_path: str,
    correlation_id: str,
) -> ProcessedInvoice:
    if not classification.is_likely_duplicate and extracted.vendor_name:
        duplicates = cosmos.query_recent_invoices(
            vendor_name=extracted.vendor_name,
            total_amount=extracted.total_amount,
            invoice_date=extracted.invoice_date,
        )
        if duplicates:
            classification.is_likely_duplicate = True
            if "potential_duplicate" not in classification.anomaly_flags:
                classification.anomaly_flags.append("potential_duplicate")
            logger.info("Detected potential duplicate: %d matches", len(duplicates))

    line_items_dicts = [asdict(li) for li in extracted.line_items]

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()

    return ProcessedInvoice(
        id=invoice_id,
        user_id=user_id,
        source=source,
        blob_path=blob_path,
        status="processed",
        vendor_name=extracted.vendor_name,
        vendor_address=extracted.vendor_address,
        customer_name=extracted.customer_name,
        invoice_number=extracted.invoice_number,
        invoice_date=extracted.invoice_date,
        due_date=extracted.due_date,
        purchase_order=extracted.purchase_order,
        total_amount=extracted.total_amount,
        subtotal=extracted.subtotal,
        total_tax=extracted.total_tax,
        currency=normalize_currency(extracted.currency),
        line_items=line_items_dicts,
        spend_category=classification.spend_category,
        subcategory=classification.subcategory,
        is_likely_duplicate=classification.is_likely_duplicate,
        anomaly_flags=classification.anomaly_flags,
        classification_confidence=classification.confidence,
        classification_reasoning=classification.reasoning,
        extraction_model="prebuilt-invoice",
        classification_model="",
        raw_text=extracted.raw_text[:10000],
        page_count=extracted.page_count,
        processed_at=now,
        correlation_id=correlation_id,
    )
