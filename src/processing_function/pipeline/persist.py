from __future__ import annotations

import logging

from src.common.config.settings import get_settings
from src.common.models.contracts import ProcessedInvoice
from src.processing_function.adapters.cosmos_client import CosmosAdapter
from src.processing_function.adapters.openai_client import AzureOpenAIAdapter
from src.processing_function.adapters.search_client import SearchAdapter

logger = logging.getLogger(__name__)

MAX_CHUNK_CHARS = 4000


def persist_invoice(
    record: ProcessedInvoice,
    cosmos: CosmosAdapter,
    search: SearchAdapter,
    ai: AzureOpenAIAdapter,
) -> None:
    cosmos.upsert_invoice(record.to_dict())
    logger.info("Persisted invoice %s to Cosmos", record.id)

    _index_to_search(record, search, ai)


def _index_to_search(
    record: ProcessedInvoice,
    search: SearchAdapter,
    ai: AzureOpenAIAdapter,
) -> None:
    s = get_settings()
    text = record.raw_text or ""
    if not text.strip():
        return

    chunks = _chunk_text(text, MAX_CHUNK_CHARS)
    metadata = {
        "vendor_name": record.vendor_name,
        "invoice_number": record.invoice_number,
        "spend_category": record.spend_category,
        "invoice_date": record.invoice_date,
        "total_amount": record.total_amount,
        "user_id": record.user_id,
    }

    docs = []
    for i, chunk in enumerate(chunks):
        embedding = None
        if s.SEARCH_USE_EMBEDDINGS:
            try:
                embedding = ai.embed(chunk)
            except Exception as exc:
                logger.warning("Embedding failed for chunk %d: %s", i, exc)

        doc = search.build_search_document(
            invoice_id=record.id,
            chunk_id=i,
            content=chunk,
            metadata=metadata,
            embedding=embedding,
        )
        docs.append(doc)

    search.upload_documents(docs)
    logger.info("Indexed %d chunks for invoice %s", len(docs), record.id)


def _chunk_text(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            newline_pos = text.rfind("\n", start, end)
            if newline_pos > start + max_chars // 2:
                end = newline_pos + 1
        chunks.append(text[start:end])
        start = end
    return chunks
