"""Structured JSON logging, shared by every service.

Kept dependency-free (stdlib `logging` + `json`) so the shared library
doesn't force a logging-framework choice on every microservice. Ships to
stdout; in AWS this is picked up by the ECS awslogs driver into CloudWatch
per ARCHITECTURE.md §10.
"""

from __future__ import annotations

import logging
import sys
import time
from typing import Any

_REDACT_KEYS = {"password", "password_hash", "token", "access_token", "refresh_token", "authorization"}


class JsonFormatter(logging.Formatter):
    def __init__(self, service_name: str) -> None:
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        import json

        payload: dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)),
            "level": record.levelname,
            "service": self.service_name,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        extra = getattr(record, "extra_fields", None)
        if isinstance(extra, dict):
            for key, value in extra.items():
                payload[key] = "[redacted]" if key.lower() in _REDACT_KEYS else value

        return json.dumps(payload, default=str)


def configure_logging(service_name: str, level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(level.upper())
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(service_name))
    root.addHandler(handler)

    # Keep noisy third-party loggers at a saner default.
    for noisy in ("uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(max(logging.WARNING, root.level))


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
