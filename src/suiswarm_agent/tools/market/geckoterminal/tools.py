"""LLM-facing GeckoTerminal tools (thin async wrappers over the service)."""

from __future__ import annotations

from typing import Literal

from langchain_core.tools import tool

from suiswarm_agent.tools.market.geckoterminal.service import get_geckoterminal_service


@tool
async def geckoterminal_networks(page: int = 1) -> dict:
    """Fetch GeckoTerminal supported network IDs for on-chain tools."""
    return await get_geckoterminal_service().networks(page)


@tool
async def geckoterminal_dexes(network: str, page: int = 1) -> dict:
    """Fetch supported DEX IDs for a GeckoTerminal network."""
    return await get_geckoterminal_service().dexes(network, page)


@tool
async def geckoterminal_onchain_token_price(network: str, addresses: str) -> dict:
    """Fetch on-chain token prices by network ID and contract address using GeckoTerminal."""
    return await get_geckoterminal_service().onchain_token_price(network, addresses)


@tool
async def geckoterminal_onchain_token_info(network: str, address: str) -> dict:
    """Fetch on-chain token metadata, GT score, holder distribution, and safety fields."""
    return await get_geckoterminal_service().onchain_token_info(network, address)


@tool
async def geckoterminal_token_top_pools(network: str, token_address: str, page: int = 1) -> dict:
    """Fetch top liquidity/volume pools for an on-chain token."""
    return await get_geckoterminal_service().token_top_pools(network, token_address, page)


@tool
async def geckoterminal_trending_pools(
    network: str | None = None,
    duration: Literal["5m", "1h", "6h", "24h"] = "24h",
    page: int = 1,
) -> dict:
    """Fetch trending DEX pools across all networks or within one network."""
    return await get_geckoterminal_service().trending_pools(network, duration, page)


@tool
async def geckoterminal_new_pools(network: str | None = None, page: int = 1) -> dict:
    """Fetch newly created GeckoTerminal pools across all networks or within one network."""
    return await get_geckoterminal_service().new_pools(network, page)


@tool
async def geckoterminal_search_pools(
    query: str,
    network: str | None = None,
    page: int = 1,
) -> dict:
    """Search GeckoTerminal pools and tokens by symbol, name, token address, or pool address."""
    return await get_geckoterminal_service().search_pools(query, network, page)


GECKOTERMINAL_TOOLS = [
    geckoterminal_networks,
    geckoterminal_dexes,
    geckoterminal_onchain_token_price,
    geckoterminal_onchain_token_info,
    geckoterminal_token_top_pools,
    geckoterminal_trending_pools,
    geckoterminal_new_pools,
    geckoterminal_search_pools,
]
