"""Langfuse 4.x tracing wiring (optional, lazily imported).

Langfuse 4 is OTEL-based: the global client is configured once via ``Langfuse(...)``,
and ``CallbackHandler()`` attaches to LangChain/LangGraph runs using that client.
Session/user/tags are passed through the run config ``metadata`` using the
``langfuse_*`` keys honored by the LangChain integration.

Everything degrades gracefully: if Langfuse is not configured, callbacks are empty
and nothing is sent.
"""

from __future__ import annotations

from typing import Any

from suiswarm_agent.config.settings import Settings, get_settings
from suiswarm_agent.core.constants import LANGFUSE_TAGS
from suiswarm_agent.core.logging import get_logger

logger = get_logger(__name__)

_configured = False


def configure_langfuse(settings: Settings | None = None) -> bool:
    """Initialize the global Langfuse client if credentials are present.

    Returns ``True`` when tracing is active. Safe to call multiple times.
    """
    global _configured
    settings = settings or get_settings()
    if not settings.langfuse.enabled:
        return False
    if _configured:
        return True
    try:
        from langfuse import Langfuse

        Langfuse(
            public_key=settings.langfuse.public_key.get_secret_value(),  # type: ignore[union-attr]
            secret_key=settings.langfuse.secret_key.get_secret_value(),  # type: ignore[union-attr]
            host=settings.langfuse.host,
        )
        _configured = True
        logger.info("Langfuse tracing enabled (host=%s)", settings.langfuse.host)
    except Exception as exc:  # pragma: no cover - optional dependency / network
        logger.warning("Langfuse init failed; tracing disabled: %s", exc)
        _configured = False
    return _configured


def langfuse_run_config(
    *,
    session_id: str,
    user_id: str | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Build a LangGraph/LangChain run config that traces to Langfuse.

    Returns ``{}`` when tracing is disabled so callers can spread it unconditionally.
    """
    settings = settings or get_settings()
    if not configure_langfuse(settings):
        return {}
    try:
        from langfuse.langchain import CallbackHandler

        metadata: dict[str, Any] = {
            "langfuse_session_id": session_id,
            "langfuse_tags": LANGFUSE_TAGS,
        }
        if user_id:
            metadata["langfuse_user_id"] = user_id
        return {"callbacks": [CallbackHandler()], "metadata": metadata, "tags": LANGFUSE_TAGS}
    except Exception as exc:  # pragma: no cover
        logger.warning("Langfuse callback unavailable: %s", exc)
        return {}


def flush_langfuse() -> None:
    """Flush queued events (important for short-lived CLI runs)."""
    if not _configured:
        return
    try:
        from langfuse import get_client

        get_client().flush()
    except Exception as exc:  # pragma: no cover
        logger.debug("Langfuse flush skipped: %s", exc)
