"""Storage/blob tools for the SpendAnalyzer agent."""
from __future__ import annotations

import json
from typing import Annotated

from agent_framework import tool

from api.adapters import blob_adapter
from api.common.config import get_api_settings


@tool
def get_document_url(
    blob_path: Annotated[str, "Blob path of the invoice document"],
    expiry_hours: Annotated[int, "How many hours the link should be valid"] = 1,
) -> str:
    """Generate a time-limited download URL for an invoice document. Use when the user wants to view or download the original file."""
    s = get_api_settings()
    url = blob_adapter.generate_sas_url(
        container=s.UPLOADS_CONTAINER_NAME,
        blob_path=blob_path,
        expiry_hours=expiry_hours,
    )
    return json.dumps({"url": url, "expires_in_hours": expiry_hours})


@tool
def export_data(
    data_json: Annotated[str, "JSON array of data to export"],
    filename: Annotated[str, "Desired filename, e.g. 'spend_report.csv'"],
    format: Annotated[str, "Export format: 'csv' or 'json'"] = "csv",
) -> str:
    """Export data as a downloadable file. Prefer using code interpreter for complex exports with charts."""
    return json.dumps({
        "hint": "For complex exports with formatting or charts, use the code interpreter instead.",
        "data_received_length": len(data_json),
        "suggested_filename": filename,
    })
