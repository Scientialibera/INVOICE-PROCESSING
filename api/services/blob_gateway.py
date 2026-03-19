"""Loads prompts and configuration from Azure Blob Storage with local fallback."""
from __future__ import annotations

import logging
import pathlib

from api.adapters.blob_adapter import download_blob_text
from api.common.config import get_api_settings

logger = logging.getLogger(__name__)

_API_ROOT = pathlib.Path(__file__).resolve().parent.parent


def load_system_prompt() -> str:
    s = get_api_settings()
    blob_name = s.AGENT_SYSTEM_PROMPT_BLOB

    try:
        content = download_blob_text(s.PROMPTS_CONTAINER_NAME, blob_name)
        if content:
            logger.info("Loaded system prompt from blob: %s", blob_name)
            return content
    except Exception as exc:
        logger.warning("Blob prompt load failed: %s", exc)

    local_path = _API_ROOT.parent / "deploy" / "assets" / "prompts" / blob_name.replace("/", pathlib.os.sep)
    if local_path.exists():
        logger.info("Loaded system prompt from local fallback: %s", local_path)
        return local_path.read_text(encoding="utf-8")

    logger.warning("System prompt not found; using default")
    return "You are SpendAnalyzer, an assistant that helps users analyze their invoices and spending."
