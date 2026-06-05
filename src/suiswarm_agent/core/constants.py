"""Centralized constants and shared identifiers.

Operational/tunable values live in :mod:`suiswarm_agent.config.settings`. This module
only holds fixed identifiers that are not meant to be configured at runtime.
"""

from __future__ import annotations

from enum import StrEnum

APP_NAME = "suiswarm-agent"
USER_AGENT = "suiswarm-agent/0.2 (+https://github.com/suiswarm)"

# Langfuse trace tags applied to every run.
LANGFUSE_TAGS = ["suiswarm-agent", "swarm", "langgraph"]


class AgentName(StrEnum):
    """Stable names for the swarm members (used for routing, tracing, handoffs)."""

    SUPERVISOR = "supervisor"
    SUI_ONCHAIN = "sui_onchain_agent"
    MARKET = "market_agent"
    RESEARCH = "research_agent"


class ToolGroup(StrEnum):
    """Logical grouping for tools, surfaced to the supervisor as compact summaries."""

    SUI = "sui"
    MARKET = "market"
    WEB = "web"
    SYSTEM = "system"
