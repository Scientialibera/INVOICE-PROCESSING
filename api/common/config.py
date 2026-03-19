from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class ApiSettings:
    STORAGE_ACCOUNT_NAME: str = ""
    UPLOADS_CONTAINER_NAME: str = "uploads"
    PROMPTS_CONTAINER_NAME: str = "prompts"

    COSMOS_ENDPOINT: str = ""
    COSMOS_DATABASE_NAME: str = "spend"
    COSMOS_INVOICES_CONTAINER: str = "invoices"
    COSMOS_SESSIONS_CONTAINER: str = "user_sessions"

    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_DEPLOYMENT: str = ""
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: str = ""
    AZURE_OPENAI_API_VERSION: str = "2025-01-01-preview"

    SEARCH_ENDPOINT: str = ""
    SEARCH_INDEX: str = "invoice-content-index"

    AGENT_NAME: str = "SpendAnalyzer"
    AGENT_SYSTEM_PROMPT_BLOB: str = "assistant/system_prompt_v1.txt"
    AGENT_ENABLE_CODE_INTERPRETER: bool = True

    ENTRA_TENANT_ID: str = ""
    ENTRA_API_CLIENT_ID: str = ""

    SERVICEBUS_FQDN: str = ""
    SERVICEBUS_QUEUE_NAME: str = "q-invoice-process"


@lru_cache(maxsize=1)
def get_api_settings() -> ApiSettings:
    kwargs = {}
    for f in ApiSettings.__dataclass_fields__:
        env_val = os.environ.get(f)
        if env_val is not None:
            ftype = ApiSettings.__dataclass_fields__[f].type
            if ftype == "bool":
                kwargs[f] = env_val.lower() in ("true", "1", "yes")
            else:
                kwargs[f] = env_val
    return ApiSettings(**kwargs)
