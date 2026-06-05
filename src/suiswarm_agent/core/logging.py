"""Structured logging setup with a per-request/session correlation id.

Call :func:`configure_logging` once at process start (CLI/API entrypoints). Everywhere
else use :func:`get_logger`. Attach a correlation id for the duration of a turn with
:func:`bind_correlation_id`.
"""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar

_ROOT = "suiswarm_agent"
_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)
_configured = False


class _CorrelationFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = _correlation_id.get() or "-"
        return True


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "correlation_id": getattr(record, "correlation_id", "-"),
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str = "INFO", *, json_format: bool = False) -> None:
    """Configure the ``suiswarm_agent`` logger. Idempotent."""
    global _configured
    logger = logging.getLogger(_ROOT)
    logger.setLevel(level.upper())
    logger.propagate = False
    # Replace handlers so repeated calls (tests, reload) don't duplicate output.
    for handler in list(logger.handlers):
        logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stderr)
    handler.addFilter(_CorrelationFilter())
    if json_format:
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)-7s [%(correlation_id)s] %(name)s: %(message)s",
                datefmt="%H:%M:%S",
            )
        )
    logger.addHandler(handler)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger under the ``suiswarm_agent`` root."""
    if name == _ROOT or name.startswith(_ROOT + "."):
        return logging.getLogger(name)
    return logging.getLogger(f"{_ROOT}.{name}")


def bind_correlation_id(value: str) -> None:
    """Bind a correlation id for the current context (session/request)."""
    _correlation_id.set(value)


def get_correlation_id() -> str | None:
    return _correlation_id.get()
