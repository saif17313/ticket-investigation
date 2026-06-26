"""Structured JSON logging configuration.

Logging is configured once at process startup. The output is plain JSON to
stdout so it is easy to ship to any log aggregator (CloudWatch, Loki, ELK).
Sensitive values (API keys, secrets, request bodies) must never be logged —
that responsibility lies with the callers, not this module.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


class _JsonFormatter(logging.Formatter):
    """Render every log record as a single JSON line."""

    # Standard ``LogRecord`` attributes we never want to echo verbatim because
    # they contain call-site noise; everything else is forwarded under ``extra``.
    _RESERVED = {
        "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
        "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
        "created", "msecs", "relativeCreated", "thread", "threadName",
        "processName", "process", "message", "asctime", "taskName",
    }

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key in self._RESERVED or key.startswith("_"):
                continue
            payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging exactly once.

    Idempotent: safe to call from the FastAPI lifespan and from tests.
    """

    root = logging.getLogger()
    if getattr(root, "_qs_configured", False):
        root.setLevel(level)
        return

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(_JsonFormatter())

    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    root._qs_configured = True  # type: ignore[attr-defined]
