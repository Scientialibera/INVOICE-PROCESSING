from __future__ import annotations

import logging

from src.common.config.settings import load_prompt, load_function_definition
from src.common.models.contracts import Classification, ExtractedInvoice
from src.processing_function.adapters.openai_client import AzureOpenAIAdapter

logger = logging.getLogger(__name__)


def _build_classification_context(extracted: ExtractedInvoice) -> str:
    lines = [
        f"Vendor: {extracted.vendor_name}",
        f"Invoice Number: {extracted.invoice_number}",
        f"Date: {extracted.invoice_date}",
        f"Due Date: {extracted.due_date}",
        f"Total: {extracted.total_amount} {extracted.currency}",
        f"Subtotal: {extracted.subtotal}",
        f"Tax: {extracted.total_tax}",
        f"PO: {extracted.purchase_order}",
        f"Customer: {extracted.customer_name}",
        f"Line Items ({len(extracted.line_items)}):",
    ]
    for i, li in enumerate(extracted.line_items[:20], 1):
        lines.append(f"  {i}. {li.description} | qty={li.quantity} | unit_price={li.unit_price} | amount={li.amount}")

    if extracted.raw_text:
        truncated = extracted.raw_text[:3000]
        lines.append(f"\n--- Raw Text (first 3000 chars) ---\n{truncated}")

    return "\n".join(lines)


def classify_invoice(extracted: ExtractedInvoice, adapter: AzureOpenAIAdapter) -> Classification:
    logger.info("Classifying invoice...")
    prompt = load_prompt("classification", "classify_invoice_v1")
    func_def = load_function_definition("classification", "classify_invoice_v1")
    context = _build_classification_context(extracted)

    result = adapter.classify_invoice(prompt, context, func_def)
    logger.info(
        "Classified: category=%s/%s, confidence=%.2f, duplicate=%s, anomalies=%s",
        result.spend_category,
        result.subcategory,
        result.confidence,
        result.is_likely_duplicate,
        result.anomaly_flags,
    )
    return result
