from __future__ import annotations

import logging

from src.common.models.contracts import ExtractedInvoice
from src.processing_function.adapters.doc_intelligence_client import DocIntelligenceAdapter

logger = logging.getLogger(__name__)


def extract_invoice(content: bytes, adapter: DocIntelligenceAdapter) -> ExtractedInvoice:
    logger.info("Extracting invoice fields with prebuilt-invoice...")
    result = adapter.extract_invoice(content)
    logger.info(
        "Extracted: vendor=%s, total=%s, %d line items, %d pages",
        result.vendor_name,
        result.total_amount,
        len(result.line_items),
        result.page_count,
    )
    return result
