"""Maps user OIDs to Assistants API thread IDs via Cosmos DB."""
from __future__ import annotations

import logging

from api.adapters import cosmos_adapter

logger = logging.getLogger(__name__)


def get_session(user_id: str) -> dict:
    return cosmos_adapter.get_or_create_session(user_id)


def get_thread_id(user_id: str) -> str | None:
    session = get_session(user_id)
    return session.get("thread_id")


def set_thread_id(user_id: str, thread_id: str) -> None:
    cosmos_adapter.update_session(user_id, {"thread_id": thread_id})
    logger.info("Updated session for user %s with thread %s", user_id, thread_id)
