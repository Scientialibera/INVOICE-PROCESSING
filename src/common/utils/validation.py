from __future__ import annotations

import re
from typing import Any


SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif"}


def is_supported_file(blob_name: str) -> bool:
    ext = "." + blob_name.rsplit(".", 1)[-1].lower() if "." in blob_name else ""
    return ext in SUPPORTED_EXTENSIONS


def safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def normalize_currency(raw: str | None) -> str:
    if not raw:
        return "USD"
    cleaned = raw.strip().upper()
    if cleaned in ("USD", "EUR", "GBP", "CAD", "AUD", "JPY"):
        return cleaned
    return "USD"


def sanitize_for_cosmos_id(*parts: str) -> str:
    raw = "|".join(parts)
    return re.sub(r"[^a-zA-Z0-9_\-|.]", "_", raw)
