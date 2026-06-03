from typing import Any, Literal

import httpx
from langchain_core.tools import tool

from suiswarm_agent.settings import get_settings

COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"


def _auth_headers() -> dict[str, str]:
    api_key = get_settings().coingecko_demo_api_key
    if not api_key:
        raise ValueError(
            "Missing COINGECKO_DEMO_API_KEY. Add your CoinGecko Demo API key to .env."
        )
    return {"x-cg-demo-api-key": api_key}


def _get(path: str, params: dict[str, Any] | None = None) -> Any:
    response = httpx.get(
        f"{COINGECKO_BASE_URL}{path}",
        headers=_auth_headers(),
        params={key: value for key, value in (params or {}).items() if value is not None},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def _base_response(endpoint: str, data: Any, params: dict[str, Any] | None = None) -> dict:
    return {
        "source": "coingecko",
        "plan": "demo",
        "endpoint": endpoint,
        "params": params or {},
        "data": data,
    }


def _sample_points(points: list, max_points: int) -> list:
    if max_points <= 0 or len(points) <= max_points:
        return points

    step = max(1, len(points) // max_points)
    sampled = points[::step][:max_points]
    if sampled[-1] != points[-1]:
        sampled[-1] = points[-1]
    return sampled


def _sample_chart(data: dict, max_points: int) -> dict:
    sampled = {}
    for key, value in data.items():
        sampled[key] = _sample_points(value, max_points) if isinstance(value, list) else value
    return sampled


@tool
def coingecko_search(query: str) -> dict:
    """Search CoinGecko for coin, exchange, category, and NFT IDs by name or symbol."""
    normalized_query = query.strip()
    if not normalized_query:
        raise ValueError("query is required.")

    params = {"query": normalized_query}
    data = _get("/search", params)
    return _base_response("/search", data, params)


@tool
def coingecko_trending() -> dict:
    """Fetch trending coins, NFTs, and categories from CoinGecko search trends."""
    data = _get("/search/trending")
    return _base_response("/search/trending", data)


@tool
def coingecko_search_coin_market(
    query: str,
    vs_currency: str = "usd",
    lookup: Literal["auto", "ids", "symbols", "names"] = "auto",
) -> dict:
    """Fetch live CoinGecko market data for a coin by ID, symbol, or name using the Demo API."""
    normalized_query = query.strip()
    if not normalized_query:
        raise ValueError("query is required.")

    attempts: list[tuple[str, dict[str, str]]] = []
    slug_query = normalized_query.lower().replace(" ", "-")

    if lookup in {"auto", "ids"}:
        attempts.append(("ids", {"ids": slug_query}))
    if lookup in {"auto", "symbols"}:
        attempts.append(
            (
                "symbols",
                {
                    "symbols": normalized_query.lower(),
                    "include_tokens": "top",
                },
            )
        )
    if lookup in {"auto", "names"}:
        attempts.append(("names", {"names": normalized_query}))

    last_error: str | None = None
    for matched_by, lookup_params in attempts:
        params = {
            "vs_currency": vs_currency.lower(),
            "order": "market_cap_desc",
            "per_page": "10",
            "page": "1",
            "sparkline": "false",
            "price_change_percentage": "1h,24h,7d,30d",
            **lookup_params,
        }

        try:
            data = _get("/coins/markets", params)
        except httpx.HTTPStatusError as exc:
            last_error = f"{exc.response.status_code}: {exc.response.text}"
            continue

        if isinstance(data, list) and data:
            return {
                "source": "coingecko",
                "plan": "demo",
                "endpoint": "/coins/markets",
                "matched_by": matched_by,
                "query": normalized_query,
                "vs_currency": vs_currency.lower(),
                "results": data,
            }

    return {
        "source": "coingecko",
        "plan": "demo",
        "endpoint": "/coins/markets",
        "query": normalized_query,
        "vs_currency": vs_currency.lower(),
        "results": [],
        "error": last_error,
    }


@tool
def coingecko_coin_markets(
    vs_currency: str = "usd",
    ids: str | None = None,
    symbols: str | None = None,
    category: str | None = None,
    order: Literal[
        "market_cap_desc",
        "market_cap_asc",
        "volume_desc",
        "volume_asc",
        "id_asc",
        "id_desc",
    ] = "market_cap_desc",
    per_page: int = 20,
    page: int = 1,
) -> dict:
    """Fetch ranked coin market data, optionally filtered by IDs, symbols, or category."""
    params = {
        "vs_currency": vs_currency.lower(),
        "ids": ids,
        "symbols": symbols,
        "include_tokens": "top" if symbols else None,
        "category": category,
        "order": order,
        "per_page": min(max(per_page, 1), 250),
        "page": max(page, 1),
        "sparkline": "false",
        "price_change_percentage": "1h,24h,7d,30d",
    }
    data = _get("/coins/markets", params)
    return _base_response("/coins/markets", data, params)


@tool
def coingecko_coin_details(coin_id: str) -> dict:
    """Fetch detailed metadata and market data for a CoinGecko coin ID."""
    normalized_id = coin_id.strip().lower()
    if not normalized_id:
        raise ValueError("coin_id is required.")

    params = {
        "localization": "false",
        "tickers": "false",
        "market_data": "true",
        "community_data": "false",
        "developer_data": "false",
        "sparkline": "false",
    }
    data = _get(f"/coins/{normalized_id}", params)
    return _base_response(f"/coins/{normalized_id}", data, params)


@tool
def coingecko_top_movers(
    vs_currency: str = "usd",
    duration: Literal["1h", "24h", "7d", "14d", "30d", "60d", "1y"] = "24h",
    top_coins: Literal["300", "500", "1000", "all"] = "1000",
) -> dict:
    """Fetch top gainers and losers for a duration, with Demo-safe market sorting fallback."""
    params = {
        "vs_currency": vs_currency.lower(),
        "duration": duration,
        "top_coins": top_coins,
    }
    try:
        data = _get("/coins/top_gainers_losers", params)
        return _base_response("/coins/top_gainers_losers", data, params)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code not in {401, 403}:
            raise

    fallback_params = {
        "vs_currency": vs_currency.lower(),
        "order": "market_cap_desc",
        "per_page": "250",
        "page": "1",
        "sparkline": "false",
        "price_change_percentage": duration,
    }
    markets = _get("/coins/markets", fallback_params)
    change_key = (
        "price_change_percentage_24h"
        if duration == "24h"
        else f"price_change_percentage_{duration}_in_currency"
    )
    sortable = [
        coin
        for coin in markets
        if isinstance(coin, dict) and isinstance(coin.get(change_key), int | float)
    ]
    top_gainers = sorted(sortable, key=lambda coin: coin[change_key], reverse=True)[:30]
    top_losers = sorted(sortable, key=lambda coin: coin[change_key])[:30]
    return {
        "source": "coingecko",
        "plan": "demo",
        "endpoint": "/coins/markets",
        "fallback_for": "/coins/top_gainers_losers",
        "params": fallback_params,
        "sorted_by": change_key,
        "data": {
            "top_gainers": top_gainers,
            "top_losers": top_losers,
        },
    }


@tool
def coingecko_coin_market_chart(
    coin_id: str,
    days: Literal["1", "7", "14", "30", "90", "180", "365", "max"] = "7",
    vs_currency: str = "usd",
    interval: Literal["daily", "hourly"] | None = None,
    max_points: int = 80,
) -> dict:
    """Fetch sampled historical price, market cap, and volume chart data for a coin ID."""
    normalized_id = coin_id.strip().lower()
    if not normalized_id:
        raise ValueError("coin_id is required.")

    params = {
        "vs_currency": vs_currency.lower(),
        "days": days,
        "interval": interval,
    }
    data = _get(f"/coins/{normalized_id}/market_chart", params)
    sampled = _sample_chart(data, min(max(max_points, 10), 250))
    return _base_response(f"/coins/{normalized_id}/market_chart", sampled, params)


@tool
def coingecko_coin_ohlc(
    coin_id: str,
    days: Literal["1", "7", "14", "30", "90", "180", "365", "max"] = "7",
    vs_currency: str = "usd",
    interval: Literal["daily", "hourly"] | None = None,
    max_candles: int = 80,
) -> dict:
    """Fetch sampled OHLC candlestick data for a CoinGecko coin ID."""
    normalized_id = coin_id.strip().lower()
    if not normalized_id:
        raise ValueError("coin_id is required.")

    params = {
        "vs_currency": vs_currency.lower(),
        "days": days,
        "interval": interval,
    }
    data = _get(f"/coins/{normalized_id}/ohlc", params)
    sampled = _sample_points(data, min(max(max_candles, 10), 250))
    return _base_response(f"/coins/{normalized_id}/ohlc", sampled, params)


@tool
def coingecko_token_price_by_contract(
    asset_platform_id: str,
    contract_addresses: str,
    vs_currencies: str = "usd",
) -> dict:
    """Fetch CoinGecko token prices by asset platform and contract address."""
    platform = asset_platform_id.strip().lower()
    addresses = contract_addresses.strip()
    if not platform or not addresses:
        raise ValueError("asset_platform_id and contract_addresses are required.")

    params = {
        "contract_addresses": addresses,
        "vs_currencies": vs_currencies.lower(),
        "include_market_cap": "true",
        "include_24hr_vol": "true",
        "include_24hr_change": "true",
        "include_last_updated_at": "true",
    }
    endpoint = f"/simple/token_price/{platform}"
    data = _get(endpoint, params)
    return _base_response(endpoint, data, params)


@tool
def coingecko_token_details_by_contract(
    asset_platform_id: str,
    contract_address: str,
) -> dict:
    """Fetch CoinGecko token metadata and market data by asset platform and contract address."""
    platform = asset_platform_id.strip().lower()
    address = contract_address.strip()
    if not platform or not address:
        raise ValueError("asset_platform_id and contract_address are required.")

    endpoint = f"/coins/{platform}/contract/{address}"
    data = _get(endpoint)
    return _base_response(endpoint, data)


@tool
def coingecko_global_market() -> dict:
    """Fetch global crypto market cap, volume, and market dominance data."""
    data = _get("/global")
    return _base_response("/global", data)


@tool
def coingecko_defi_market() -> dict:
    """Fetch global DeFi market data from CoinGecko."""
    data = _get("/global/decentralized_finance_defi")
    return _base_response("/global/decentralized_finance_defi", data)


@tool
def coingecko_categories(
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
    params = {"order": order}
    data = _get("/coins/categories", params)
    return _base_response("/coins/categories", data, params)


@tool
def coingecko_exchanges(per_page: int = 20, page: int = 1) -> dict:
    """Fetch exchange rankings with trust score and 24h BTC volume."""
    params = {
        "per_page": min(max(per_page, 1), 250),
        "page": max(page, 1),
    }
    data = _get("/exchanges", params)
    return _base_response("/exchanges", data, params)


@tool
def coingecko_exchange_tickers(
    exchange_id: str,
    coin_ids: str | None = None,
    page: int = 1,
) -> dict:
    """Fetch tickers and trading pairs for a CoinGecko exchange ID."""
    normalized_id = exchange_id.strip().lower()
    if not normalized_id:
        raise ValueError("exchange_id is required.")

    params = {
        "coin_ids": coin_ids,
        "page": max(page, 1),
        "order": "trust_score_desc",
        "include_exchange_logo": "true",
        "depth": "false",
    }
    endpoint = f"/exchanges/{normalized_id}/tickers"
    data = _get(endpoint, params)
    return _base_response(endpoint, data, params)


@tool
def coingecko_exchange_rates() -> dict:
    """Fetch BTC exchange rates against fiat, crypto, and commodity currencies."""
    data = _get("/exchange_rates")
    return _base_response("/exchange_rates", data)


@tool
def coingecko_nft_details(nft_id: str) -> dict:
    """Fetch NFT collection floor price, market cap, volume, and metadata by NFT ID."""
    normalized_id = nft_id.strip().lower()
    if not normalized_id:
        raise ValueError("nft_id is required.")

    endpoint = f"/nfts/{normalized_id}"
    data = _get(endpoint)
    return _base_response(endpoint, data)


@tool
def geckoterminal_networks(page: int = 1) -> dict:
    """Fetch GeckoTerminal supported network IDs for on-chain tools."""
    params = {"page": max(page, 1)}
    data = _get("/onchain/networks", params)
    return _base_response("/onchain/networks", data, params)


@tool
def geckoterminal_dexes(network: str, page: int = 1) -> dict:
    """Fetch supported DEX IDs for a GeckoTerminal network."""
    network_id = network.strip().lower()
    if not network_id:
        raise ValueError("network is required.")

    params = {"page": max(page, 1)}
    endpoint = f"/onchain/networks/{network_id}/dexes"
    data = _get(endpoint, params)
    return _base_response(endpoint, data, params)


@tool
def geckoterminal_onchain_token_price(
    network: str,
    addresses: str,
) -> dict:
    """Fetch on-chain token prices by network ID and contract address using GeckoTerminal."""
    network_id = network.strip().lower()
    normalized_addresses = addresses.strip()
    if not network_id or not normalized_addresses:
        raise ValueError("network and addresses are required.")

    params = {
        "include_market_cap": "true",
        "mcap_fdv_fallback": "true",
        "include_24hr_vol": "true",
        "include_24hr_price_change": "true",
        "include_total_reserve_in_usd": "true",
        "include_inactive_source": "true",
    }
    endpoint = f"/onchain/simple/networks/{network_id}/token_price/{normalized_addresses}"
    data = _get(endpoint, params)
    return _base_response(endpoint, data, params)


@tool
def geckoterminal_onchain_token_info(network: str, address: str) -> dict:
    """Fetch on-chain token metadata, GT score, holder distribution, and safety fields."""
    network_id = network.strip().lower()
    normalized_address = address.strip()
    if not network_id or not normalized_address:
        raise ValueError("network and address are required.")

    endpoint = f"/onchain/networks/{network_id}/tokens/{normalized_address}/info"
    data = _get(endpoint)
    return _base_response(endpoint, data)


@tool
def geckoterminal_token_top_pools(
    network: str,
    token_address: str,
    page: int = 1,
) -> dict:
    """Fetch top liquidity/volume pools for an on-chain token."""
    network_id = network.strip().lower()
    address = token_address.strip()
    if not network_id or not address:
        raise ValueError("network and token_address are required.")

    params = {
        "include": "base_token,quote_token,dex",
        "page": max(page, 1),
        "sort": "h24_volume_usd_liquidity_desc",
        "include_inactive_source": "true",
    }
    endpoint = f"/onchain/networks/{network_id}/tokens/{address}/pools"
    data = _get(endpoint, params)
    return _base_response(endpoint, data, params)


@tool
def geckoterminal_trending_pools(
    network: str | None = None,
    duration: Literal["5m", "1h", "6h", "24h"] = "24h",
    page: int = 1,
) -> dict:
    """Fetch trending DEX pools across all networks or within one network."""
    network_id = network.strip().lower() if network else None
    endpoint = (
        f"/onchain/networks/{network_id}/trending_pools"
        if network_id
        else "/onchain/networks/trending_pools"
    )
    params = {
        "include": "base_token,quote_token,dex,network" if not network_id else "base_token,quote_token,dex",
        "duration": duration,
        "page": max(page, 1),
    }
    data = _get(endpoint, params)
    return _base_response(endpoint, data, params)


@tool
def geckoterminal_new_pools(network: str | None = None, page: int = 1) -> dict:
    """Fetch newly created GeckoTerminal pools across all networks or within one network."""
    network_id = network.strip().lower() if network else None
    endpoint = (
        f"/onchain/networks/{network_id}/new_pools"
        if network_id
        else "/onchain/networks/new_pools"
    )
    params = {
        "include": "base_token,quote_token,dex,network" if not network_id else "base_token,quote_token,dex",
        "page": max(page, 1),
    }
    data = _get(endpoint, params)
    return _base_response(endpoint, data, params)


@tool
def geckoterminal_search_pools(
    query: str,
    network: str | None = None,
    page: int = 1,
) -> dict:
    """Search GeckoTerminal pools and tokens by symbol, name, token address, or pool address."""
    normalized_query = query.strip()
    if not normalized_query:
        raise ValueError("query is required.")

    params = {
        "query": normalized_query,
        "network": network.strip().lower() if network else None,
        "include": "base_token,quote_token,dex",
        "page": max(page, 1),
    }
    data = _get("/onchain/search/pools", params)
    return _base_response("/onchain/search/pools", data, params)


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
    geckoterminal_networks,
    geckoterminal_dexes,
    geckoterminal_onchain_token_price,
    geckoterminal_onchain_token_info,
    geckoterminal_token_top_pools,
    geckoterminal_trending_pools,
    geckoterminal_new_pools,
    geckoterminal_search_pools,
]
