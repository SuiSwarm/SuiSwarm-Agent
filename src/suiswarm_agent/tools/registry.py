"""Tool registry with conditional registration.

Each group returns its tools only when the relevant upstream credential is configured,
so a missing key means the tool group is simply absent (no mid-run surprises). The swarm
assigns these groups to sub-agents.
"""

from __future__ import annotations

from langchain_core.tools import BaseTool

from suiswarm_agent.config.settings import Settings, get_settings
from suiswarm_agent.tools.base import include_if


def _load_market_tools() -> list[BaseTool]:
    from suiswarm_agent.tools.market.coingecko.tools import COINGECKO_TOOLS
    from suiswarm_agent.tools.market.geckoterminal.tools import GECKOTERMINAL_TOOLS

    return [*COINGECKO_TOOLS, *GECKOTERMINAL_TOOLS]


def _load_sui_tools() -> list[BaseTool]:
    from suiswarm_agent.tools.sui.tools import SUI_TOOLS

    return list(SUI_TOOLS)


def market_tools(settings: Settings | None = None) -> list[BaseTool]:
    """CoinGecko + GeckoTerminal tools (requires a CoinGecko Demo key)."""
    settings = settings or get_settings()
    return include_if(settings.coingecko.enabled, _load_market_tools)


def research_tools(settings: Settings | None = None) -> list[BaseTool]:
    """Web research tools (requires a Tavily key)."""
    from suiswarm_agent.tools.web.search import build_tavily_tool

    tavily = build_tavily_tool(settings)
    return [tavily] if tavily is not None else []


def system_tools(settings: Settings | None = None) -> list[BaseTool]:
    """Always-available built-in utility tools."""
    from suiswarm_agent.tools.system.builtin import SYSTEM_TOOLS

    return list(SYSTEM_TOOLS)


def sui_tools(settings: Settings | None = None) -> list[BaseTool]:
    """Sui on-chain tools (requires the NestJS Sui service to be configured)."""
    settings = settings or get_settings()
    return include_if(settings.sui_service.enabled, _load_sui_tools)


def available_tools(settings: Settings | None = None) -> dict[str, list[BaseTool]]:
    """Map of group name -> tools, filtered by configured credentials."""
    settings = settings or get_settings()
    return {
        "sui": sui_tools(settings),
        "market": market_tools(settings),
        "web": research_tools(settings),
        "system": system_tools(settings),
    }


def all_tools(settings: Settings | None = None) -> list[BaseTool]:
    """Flat list of every available tool."""
    return [tool for group in available_tools(settings).values() for tool in group]


def tool_names(settings: Settings | None = None) -> list[str]:
    return [tool.name for tool in all_tools(settings)]


async def close_clients() -> None:
    """Close any lazily-created upstream HTTP client singletons (call on shutdown)."""
    from suiswarm_agent.tools.market.coingecko.client import aclose_coingecko_client
    from suiswarm_agent.tools.sui.client import aclose_sui_client

    await aclose_coingecko_client()
    await aclose_sui_client()
