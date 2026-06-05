"""Built-in utility tools available to every agent."""

from __future__ import annotations

from datetime import UTC, datetime

from langchain_core.tools import tool


@tool
def get_utc_time() -> str:
    """Return the current UTC time in ISO 8601 format."""
    return datetime.now(UTC).isoformat()


@tool
def describe_project() -> str:
    """Describe what the SuiSwarm Agent is and what it can do."""
    return (
        "SuiSwarm Agent is a Sui-first multi-agent swarm built on LangGraph. A supervisor "
        "routes requests to specialized sub-agents: a market-data agent (CoinGecko / "
        "GeckoTerminal), a web research agent (Tavily), and a Sui on-chain agent that talks "
        "to an external NestJS Sui service over REST. Each sub-agent owns its own tools."
    )


SYSTEM_TOOLS = [get_utc_time, describe_project]
