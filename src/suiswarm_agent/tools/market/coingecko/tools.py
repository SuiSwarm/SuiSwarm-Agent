"""LLM-facing CoinGecko tools (thin async wrappers over :class:`CoinGeckoService`)."""

from __future__ import annotations

from typing import Literal

from langchain_core.tools import tool

from suiswarm_agent.tools.market.coingecko.service import get_coingecko_service


@tool
async def coingecko_search(query: str) -> dict:
    """Search CoinGecko for coin, exchange, category, and NFT IDs by name or symbol."""
    return await get_coingecko_service().search(query)


@tool
async def coingecko_trending() -> dict:
    """Fetch trending coins, NFTs, and categories from CoinGecko search trends."""
    return await get_coingecko_service().trending()


@tool
async def coingecko_search_coin_market(
    query: str,
    vs_currency: str = "usd",
    lookup: Literal["auto", "ids", "symbols", "names"] = "auto",
) -> dict:
    """Fetch live CoinGecko market data for a coin by ID, symbol, or name using the Demo API."""
    return await get_coingecko_service().search_coin_market(query, vs_currency, lookup)


@tool
async def coingecko_coin_markets(
    vs_currency: str = "usd",
    ids: str | None = None,
    symbols: str | None = None,
    category: str | None = None,
    order: Literal[
        "market_cap_desc", "market_cap_asc", "volume_desc", "volume_asc", "id_asc", "id_desc"
    ] = "market_cap_desc",
    per_page: int = 20,
    page: int = 1,
) -> dict:
    """Fetch ranked coin market data, optionally filtered by IDs, symbols, or category."""
    return await get_coingecko_service().coin_markets(
        vs_currency, ids, symbols, category, order, per_page, page
    )


@tool
async def coingecko_coin_details(coin_id: str) -> dict:
    """Fetch detailed metadata and market data for a CoinGecko coin ID."""
    return await get_coingecko_service().coin_details(coin_id)


@tool
async def coingecko_top_movers(
    vs_currency: str = "usd",
    duration: Literal["1h", "24h", "7d", "14d", "30d", "60d", "1y"] = "24h",
    top_coins: Literal["300", "500", "1000", "all"] = "1000",
) -> dict:
    """Fetch top gainers and losers for a duration, with Demo-safe market sorting fallback."""
    return await get_coingecko_service().top_movers(vs_currency, duration, top_coins)


@tool
async def coingecko_coin_market_chart(
    coin_id: str,
    days: Literal["1", "7", "14", "30", "90", "180", "365", "max"] = "7",
    vs_currency: str = "usd",
    interval: Literal["daily", "hourly"] | None = None,
    max_points: int = 80,
) -> dict:
    """Fetch sampled historical price, market cap, and volume chart data for a coin ID."""
    return await get_coingecko_service().coin_market_chart(
        coin_id, days, vs_currency, interval, max_points
    )


@tool
async def coingecko_coin_ohlc(
    coin_id: str,
    days: Literal["1", "7", "14", "30", "90", "180", "365", "max"] = "7",
    vs_currency: str = "usd",
    interval: Literal["daily", "hourly"] | None = None,
    max_candles: int = 80,
) -> dict:
    """Fetch sampled OHLC candlestick data for a CoinGecko coin ID."""
    return await get_coingecko_service().coin_ohlc(
        coin_id, days, vs_currency, interval, max_candles
    )


@tool
async def coingecko_token_price_by_contract(
    asset_platform_id: str,
    contract_addresses: str,
    vs_currencies: str = "usd",
) -> dict:
    """Fetch CoinGecko token prices by asset platform and contract address."""
    return await get_coingecko_service().token_price_by_contract(
        asset_platform_id, contract_addresses, vs_currencies
    )


@tool
async def coingecko_token_details_by_contract(
    asset_platform_id: str,
    contract_address: str,
) -> dict:
    """Fetch CoinGecko token metadata and market data by asset platform and contract address."""
    return await get_coingecko_service().token_details_by_contract(
        asset_platform_id, contract_address
    )


@tool
async def coingecko_global_market() -> dict:
    """Fetch global crypto market cap, volume, and market dominance data."""
    return await get_coingecko_service().global_market()


@tool
async def coingecko_defi_market() -> dict:
    """Fetch global DeFi market data from CoinGecko."""
    return await get_coingecko_service().defi_market()


@tool
async def coingecko_categories(
    order: Literal[
        "market_cap_desc",
        "market_cap_asc",
        "name_desc",
        "name_asc",
        "market_cap_change_24h_desc",
        "market_cap_change_24h_asc",
    ] = "market_cap_desc",
) -> dict:
    """Fetch CoinGecko category market data ranked by market cap or 24h change."""
    return await get_coingecko_service().categories(order)


@tool
async def coingecko_exchanges(per_page: int = 20, page: int = 1) -> dict:
    """Fetch exchange rankings with trust score and 24h BTC volume."""
    return await get_coingecko_service().exchanges(per_page, page)


@tool
async def coingecko_exchange_tickers(
    exchange_id: str,
    coin_ids: str | None = None,
    page: int = 1,
) -> dict:
    """Fetch tickers and trading pairs for a CoinGecko exchange ID."""
    return await get_coingecko_service().exchange_tickers(exchange_id, coin_ids, page)


@tool
async def coingecko_exchange_rates() -> dict:
    """Fetch BTC exchange rates against fiat, crypto, and commodity currencies."""
    return await get_coingecko_service().exchange_rates()


@tool
async def coingecko_nft_details(nft_id: str) -> dict:
    """Fetch NFT collection floor price, market cap, volume, and metadata by NFT ID."""
    return await get_coingecko_service().nft_details(nft_id)


COINGECKO_TOOLS = [
    coingecko_search,
    coingecko_trending,
    coingecko_search_coin_market,
    coingecko_coin_markets,
    coingecko_coin_details,
    coingecko_top_movers,
    coingecko_coin_market_chart,
    coingecko_coin_ohlc,
    coingecko_token_price_by_contract,
    coingecko_token_details_by_contract,
    coingecko_global_market,
    coingecko_defi_market,
    coingecko_categories,
    coingecko_exchanges,
    coingecko_exchange_tickers,
    coingecko_exchange_rates,
    coingecko_nft_details,
]
