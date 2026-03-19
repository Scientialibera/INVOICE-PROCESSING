from __future__ import annotations

import json
import logging
import uuid

from src.common.config.settings import get_settings
from src.common.models.contracts import InvoiceMessage
from src.processing_function.adapters.blob_storage_client import BlobStorageAdapter
from src.processing_function.adapters.cosmos_client import CosmosAdapter
from src.processing_function.adapters.doc_intelligence_client import DocIntelligenceAdapter
from src.processing_function.adapters.openai_client import AzureOpenAIAdapter
from src.processing_function.adapters.search_client import SearchAdapter
from src.processing_function.pipeline.classify import classify_invoice
from src.processing_function.pipeline.enrich import enrich_invoice
from src.processing_function.pipeline.extract import extract_invoice
from src.processing_function.pipeline.persist import persist_invoice

logger = logging.getLogger(__name__)


def process_invoice(message_body: str) -> None:
    msg_data = json.loads(message_body)
    msg = InvoiceMessage(**msg_data)

    invoice_id = str(uuid.uuid4())
    logger.info(
        "Processing invoice: blob=%s, user=%s, source=%s, correlation=%s",
        msg.blob_path, msg.user_id, msg.source, msg.correlation_id,
    )

    blob_adapter = BlobStorageAdapter()
    doc_intel = DocIntelligenceAdapter()
    ai_adapter = AzureOpenAIAdapter()
    cosmos = CosmosAdapter()
    search = SearchAdapter()

    try:
        content = blob_adapter.download_blob(msg.container_name, msg.blob_path)
        logger.info("Downloaded %d bytes from blob", len(content))

        extracted = extract_invoice(content, doc_intel)

        classification = classify_invoice(extracted, ai_adapter)

        record = enrich_invoice(
            extracted=extracted,
            classification=classification,
            cosmos=cosmos,
            invoice_id=invoice_id,
            user_id=msg.user_id,
            source=msg.source,
            blob_path=msg.blob_path,
            correlation_id=msg.correlation_id,
        )

        persist_invoice(record, cosmos, search, ai_adapter)

        logger.info("Invoice processing complete: id=%s, category=%s", invoice_id, record.spend_category)

    except Exception:
        logger.exception("Failed to process invoice: blob=%s", msg.blob_path)
        _persist_failure(cosmos, invoice_id, msg)
        raise


def _persist_failure(cosmos: CosmosAdapter, invoice_id: str, msg: InvoiceMessage) -> None:
    try:
        from datetime import datetime, timezone
        cosmos.upsert_invoice({
            "id": invoice_id,
            "user_id": msg.user_id,
            "source": msg.source,
            "blob_path": msg.blob_path,
            "status": "failed",
            "correlation_id": msg.correlation_id,
            "processed_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        logger.exception("Failed to persist failure record")
