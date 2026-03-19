from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class InvoiceMessage:
    """Message enqueued to Service Bus for processing."""
    blob_path: str
    container_name: str
    user_id: str = "system"
    source: str = "upload"              # "upload" | "email"
    upload_id: str = ""
    correlation_id: str = ""
    content_type: str = ""
    file_size_bytes: int = 0


@dataclass
class LineItem:
    description: str = ""
    quantity: float | None = None
    unit_price: float | None = None
    amount: float | None = None
    unit: str = ""
    product_code: str = ""
    tax: float | None = None


@dataclass
class ExtractedInvoice:
    """Structured output from Document Intelligence."""
    vendor_name: str = ""
    vendor_address: str = ""
    customer_name: str = ""
    customer_address: str = ""
    invoice_number: str = ""
    invoice_date: str = ""
    due_date: str = ""
    purchase_order: str = ""
    total_amount: float | None = None
    subtotal: float | None = None
    total_tax: float | None = None
    currency: str = "USD"
    line_items: list[LineItem] = field(default_factory=list)
    raw_text: str = ""
    page_count: int = 0
    confidence: float = 0.0


@dataclass
class Classification:
    """Output from OpenAI classification."""
    spend_category: str = ""
    subcategory: str = ""
    is_likely_duplicate: bool = False
    anomaly_flags: list[str] = field(default_factory=list)
    confidence: float = 0.0
    reasoning: str = ""


@dataclass
class ProcessedInvoice:
    """Full invoice record for Cosmos DB."""
    id: str = ""
    user_id: str = ""
    source: str = ""
    blob_path: str = ""
    status: str = "processed"           # "processing" | "processed" | "failed"
    vendor_name: str = ""
    vendor_address: str = ""
    customer_name: str = ""
    invoice_number: str = ""
    invoice_date: str = ""
    due_date: str = ""
    purchase_order: str = ""
    total_amount: float | None = None
    subtotal: float | None = None
    total_tax: float | None = None
    currency: str = "USD"
    line_items: list[dict] = field(default_factory=list)
    spend_category: str = ""
    subcategory: str = ""
    is_likely_duplicate: bool = False
    anomaly_flags: list[str] = field(default_factory=list)
    classification_confidence: float = 0.0
    classification_reasoning: str = ""
    extraction_model: str = "prebuilt-invoice"
    classification_model: str = ""
    raw_text: str = ""
    page_count: int = 0
    processed_at: str = ""
    correlation_id: str = ""
    tags: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        from dataclasses import asdict
        return asdict(self)
