"""Tavily web search tool (constructed lazily and only when configured).

The old implementation instantiated ``TavilySearch()`` at import time (a side effect
that broke when the key was absent). Here it is built on demand from settings.
"""

from __future__ import annotations

from langchain_core.tools import BaseTool

from suiswarm_agent.config.settings import Settings, get_settings
from suiswarm_agent.core.logging import get_logger

logger = get_logger(__name__)


def build_tavily_tool(settings: Settings | None = None) -> BaseTool | None:
    """Return a configured Tavily search tool, or ``None`` if no key is set."""
    cfg = (settings or get_settings()).tavily
    if not cfg.enabled or cfg.api_key is None:
        return None
    try:
        from langchain_tavily import TavilySearch

        return TavilySearch(
            max_results=cfg.max_results,
            topic=cfg.topic,
            include_answer=cfg.include_answer,
            search_depth=cfg.search_depth,
            tavily_api_key=cfg.api_key.get_secret_value(),
        )
    except Exception as exc:  # pragma: no cover - optional dependency / bad key
        logger.warning("Tavily tool unavailable: %s", exc)
        return None
