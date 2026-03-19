from __future__ import annotations

import json
import logging
import os
import pathlib
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_SRC_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent


@dataclass(frozen=True)
class Settings:
    STORAGE_ACCOUNT_NAME: str = ""
    UPLOADS_CONTAINER_NAME: str = "uploads"
    PROMPTS_CONTAINER_NAME: str = "prompts"
    FUNCTION_DEFINITIONS_CONTAINER_NAME: str = "function-definitions"

    SERVICEBUS_QUEUE_NAME: str = "q-invoice-process"

    COSMOS_ENDPOINT: str = ""
    COSMOS_DATABASE_NAME: str = "spend"
    COSMOS_INVOICES_CONTAINER: str = "invoices"

    AOAI_ENDPOINT: str = ""
    AOAI_DEPLOYMENT: str = ""
    AOAI_DEPLOYMENT_EMBEDDING: str = ""
    AOAI_API_VERSION: str = "2025-01-01-preview"

    DOCINTEL_ENDPOINT: str = ""

    SEARCH_ENDPOINT: str = ""
    SEARCH_INDEX: str = "invoice-content-index"
    SEARCH_USE_EMBEDDINGS: bool = True

    ACTIVE_MODEL_PROFILE: str = "default"
    CLASSIFICATION_PROMPT_BLOB_NAME: str = "classification/classify_invoice_v1.txt"
    CLASSIFICATION_FUNC_DEF_BLOB_NAME: str = "classification/classify_invoice_v1.json"
    CONFIDENCE_THRESHOLD: float = 0.90


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    kwargs: dict[str, Any] = {}
    for f in Settings.__dataclass_fields__:
        env_val = os.environ.get(f)
        if env_val is not None:
            ftype = Settings.__dataclass_fields__[f].type
            if ftype == "bool":
                kwargs[f] = env_val.lower() in ("true", "1", "yes")
            elif ftype == "float":
                kwargs[f] = float(env_val)
            else:
                kwargs[f] = env_val
    return Settings(**kwargs)


def load_model_profile(profile_name: str | None = None) -> dict:
    name = profile_name or get_settings().ACTIVE_MODEL_PROFILE
    local_path = _SRC_ROOT / "model_profiles" / f"{name}.yaml"
    if not local_path.exists():
        return {}
    with open(local_path) as f:
        profile = yaml.safe_load(f) or {}
    s = get_settings()
    for key in ("classification_model",):
        if profile.get(key) == "${AOAI_DEPLOYMENT}":
            profile[key] = s.AOAI_DEPLOYMENT
    return profile


def _load_from_blob(container: str, blob_name: str) -> str | None:
    s = get_settings()
    if not s.STORAGE_ACCOUNT_NAME or not container:
        return None
    try:
        from azure.storage.blob import BlobServiceClient
        from src.common.auth.credentials import get_credential

        client = BlobServiceClient(
            account_url=f"https://{s.STORAGE_ACCOUNT_NAME}.blob.core.windows.net",
            credential=get_credential(),
        )
        data = client.get_blob_client(container, blob_name).download_blob().readall()
        return data.decode("utf-8")
    except Exception as exc:
        logger.warning("Blob read failed (%s/%s): %s", container, blob_name, exc)
        return None


def load_prompt(kind: str, name: str) -> str:
    s = get_settings()
    blob_name_env = f"{kind.upper()}_PROMPT_BLOB_NAME"
    blob_name = os.environ.get(blob_name_env, f"{kind}/{name}.txt")
    content = _load_from_blob(s.PROMPTS_CONTAINER_NAME, blob_name)
    if content:
        return content
    local_path = _SRC_ROOT / "prompts" / kind / f"{name}.txt"
    if local_path.exists():
        return local_path.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Prompt not found: {kind}/{name}")


def load_function_definition(kind: str, name: str) -> dict:
    s = get_settings()
    blob_name_env = f"{kind.upper()}_FUNC_DEF_BLOB_NAME"
    blob_name = os.environ.get(blob_name_env, f"{kind}/{name}.json")
    content = _load_from_blob(s.FUNCTION_DEFINITIONS_CONTAINER_NAME, blob_name)
    if content:
        return json.loads(content)
    local_path = _SRC_ROOT / "function_definitions" / kind / f"{name}.json"
    if local_path.exists():
        return json.loads(local_path.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"Function definition not found: {kind}/{name}")
