import logging
import os

from applicationinsights import TelemetryClient


def get_telemetry_client() -> TelemetryClient | None:
    key = os.environ.get("APPINSIGHTS_INSTRUMENTATIONKEY")
    if not key:
        return None
    return TelemetryClient(key)


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
