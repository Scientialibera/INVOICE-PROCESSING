from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict

from azure.servicebus import ServiceBusClient, ServiceBusMessage

from src.common.auth.credentials import get_credential
from src.common.config.settings import get_settings
from src.common.models.contracts import InvoiceMessage
from src.common.utils.validation import is_supported_file

logger = logging.getLogger(__name__)


def _blob_name_from_event(event_data: dict) -> str | None:
    subject = event_data.get("subject", "")
    if "/blobs/" in subject:
        return subject.split("/blobs/", 1)[1]
    url = event_data.get("data", {}).get("url", "")
    if "/blobs/" in url:
        return url.split("/blobs/", 1)[1]
    return None


def _parse_blob_path(blob_name: str) -> dict:
    parts = blob_name.split("/")
    if len(parts) >= 3 and parts[0] == "email":
        return {"source": "email", "user_id": "email", "upload_id": parts[1]}
    if len(parts) >= 3:
        return {"source": "upload", "user_id": parts[0], "upload_id": parts[1]}
    return {"source": "unknown", "user_id": "unknown", "upload_id": ""}


def handle_event_grid(event_json: str) -> None:
    events = json.loads(event_json)
    if isinstance(events, dict):
        events = [events]

    s = get_settings()

    for event in events:
        event_type = event.get("eventType", "")
        if event_type != "Microsoft.Storage.BlobCreated":
            logger.info("Ignoring event type: %s", event_type)
            continue

        blob_name = _blob_name_from_event(event)
        if not blob_name:
            logger.warning("Could not extract blob name from event")
            continue

        if not is_supported_file(blob_name):
            logger.info("Unsupported file type, skipping: %s", blob_name)
            continue

        parsed = _parse_blob_path(blob_name)
        content_length = event.get("data", {}).get("contentLength", 0)

        msg = InvoiceMessage(
            blob_path=blob_name,
            container_name=s.UPLOADS_CONTAINER_NAME,
            user_id=parsed["user_id"],
            source=parsed["source"],
            upload_id=parsed["upload_id"],
            correlation_id=str(uuid.uuid4()),
            content_type=event.get("data", {}).get("contentType", ""),
            file_size_bytes=content_length,
        )

        _enqueue_message(msg, s)
        logger.info("Enqueued invoice message: %s (correlation=%s)", blob_name, msg.correlation_id)


def _enqueue_message(msg: InvoiceMessage, s) -> None:
    fqdn = f"{s.SERVICEBUS_QUEUE_NAME}".replace("q-", "")
    sb_fqdn = f"sbns-{fqdn.split('-')[0] if '-' in fqdn else fqdn}.servicebus.windows.net"
    ns_env = f"{get_settings().STORAGE_ACCOUNT_NAME}".replace("st", "sbns-")

    import os
    sb_conn_fqdn = os.environ.get("SERVICEBUS_CONNECTION__fullyQualifiedNamespace", "")
    if not sb_conn_fqdn:
        logger.error("SERVICEBUS_CONNECTION__fullyQualifiedNamespace not set")
        return

    client = ServiceBusClient(sb_conn_fqdn, credential=get_credential())
    with client:
        sender = client.get_queue_sender(queue_name=s.SERVICEBUS_QUEUE_NAME)
        with sender:
            body = json.dumps(asdict(msg))
            sender.send_messages(ServiceBusMessage(body=body))
