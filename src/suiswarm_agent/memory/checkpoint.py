"""LangGraph checkpointer backends.

* ``memory``   — :class:`InMemorySaver` (default; per-process, no persistence).
* ``sqlite``   — :class:`AsyncSqliteSaver` (single-node persistence; dev / CLI).
* ``postgres`` — :class:`AsyncPostgresSaver` (multi-user / hosted API).

The sqlite/postgres savers own a connection, so they are exposed through an async
context manager (:func:`checkpointer_context`). Long-lived callers (the API lifespan,
the CLI session loop) wrap their work in it; the module-level graph used by the
LangGraph dev server falls back to in-memory via :func:`build_checkpointer`.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver

from suiswarm_agent.config.settings import Settings, get_settings
from suiswarm_agent.core.exceptions import ConfigError
from suiswarm_agent.core.logging import get_logger

logger = get_logger(__name__)


def build_checkpointer(settings: Settings | None = None) -> BaseCheckpointSaver:
    """Return a connection-less checkpointer (always in-memory).

    For ``sqlite``/``postgres`` use :func:`checkpointer_context` instead — those
    backends require managed connections.
    """
    return InMemorySaver()


@asynccontextmanager
async def checkpointer_context(
    settings: Settings | None = None,
) -> AsyncIterator[BaseCheckpointSaver]:
    """Yield a checkpointer for the configured backend, managing its lifecycle."""
    settings = settings or get_settings()
    backend = settings.persistence.backend

    if backend == "memory":
        yield InMemorySaver()
        return

    if backend == "sqlite":
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        path = settings.persistence.sqlite_path
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        async with AsyncSqliteSaver.from_conn_string(path) as saver:
            await saver.setup()
            logger.info("Using SQLite checkpointer at %s", path)
            yield saver
        return

    if backend == "postgres":
        dsn = settings.persistence.postgres_dsn
        if not dsn:
            raise ConfigError("persistence.backend=postgres requires PERSISTENCE__POSTGRES_DSN.")
        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ConfigError(
                "Postgres checkpointer requires the 'langgraph-checkpoint-postgres' package."
            ) from exc
        async with AsyncPostgresSaver.from_conn_string(dsn) as saver:
            await saver.setup()
            logger.info("Using Postgres checkpointer")
            yield saver
        return

    raise ConfigError(f"Unknown persistence backend: {backend}")
