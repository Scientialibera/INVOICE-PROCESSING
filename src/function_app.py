import json
import logging

import azure.functions as func

from src.common.logging.telemetry import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

app = func.FunctionApp()


@app.function_name("InvoiceIntake")
@app.event_grid_trigger(arg_name="event")
def invoice_intake(event: func.EventGridEvent) -> None:
    """Event Grid trigger: fires on BlobCreated in the uploads container."""
    logger.info("InvoiceIntake triggered: subject=%s, type=%s", event.subject, event.event_type)

    event_data = {
        "id": event.id,
        "subject": event.subject,
        "eventType": event.event_type,
        "data": event.get_json(),
    }

    from src.intake_function.handler import handle_event_grid
    handle_event_grid(json.dumps(event_data))


@app.function_name("InvoiceProcess")
@app.service_bus_queue_trigger(
    arg_name="msg",
    queue_name="%SERVICEBUS_QUEUE_NAME%",
    connection="SERVICEBUS_CONNECTION",
)
def invoice_process(msg: func.ServiceBusMessage) -> None:
    """Service Bus trigger: processes a single invoice."""
    body = msg.get_body().decode("utf-8")
    logger.info("InvoiceProcess triggered: message_id=%s", msg.message_id)

    from src.processing_function.handler import process_invoice
    process_invoice(body)
