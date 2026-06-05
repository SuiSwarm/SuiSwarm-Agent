"""CoinGecko domain logic (async). Pure data access — no LLM/tool concerns here."""

from __future__ import annotations

from typing import Any, Literal
from urllib.parse import quote

from suiswarm_agent.core.exceptions import RateLimitedError, UpstreamAPIError
from suiswarm_agent.tools.market.coingecko.client import CoinGeckoClient, get_coingecko_client
from suiswarm_agent.tools.market.coingecko.models import base_response, sample_chart, sample_points

# /coins/markets accepts these price_change_percentage windows (note: 60d is NOT one of
# them, although /coins/top_gainers_losers does accept it).
_MARKETS_CHANGE_WINDOWS = {"1h", "24h", "7d", "14d", "30d", "1y"}

Order = Literal[
    "market_cap_desc", "market_cap_asc", "volume_desc", "volume_asc", "id_asc", "id_desc"
]
Duration = Literal["1h", "24h", "7d", "14d", "30d", "60d", "1y"]
Days = Literal["1", "7", "14", "30", "90", "180", "365", "max"]


def _clamp(value: int, low: int, high: int) -> int:
    return min(max(value, low), high)


def _seg(value: str) -> str:
    """URL-encode a user-supplied path segment."""
    return quote(value.strip(), safe="")


class CoinGeckoService:
    def __init__(self, client: CoinGeckoClient | None = None) -> None:
        self._client = client or get_coingecko_client()

    async def search(self, query: str) -> dict[str, Any]:
        q = query.strip()
        if not q:
            raise ValueError("query is required.")
        params = {"query": q}
        data = await self._client.get("/search", params)
        return base_response("/search", data, params)

    async def trending(self) -> dict[str, Any]:
        data = await self._client.get("/search/trending")
        return base_response("/search/trending", data)

    async def search_coin_market(
        self,
        query: str,
        vs_currency: str = "usd",
        lookup: Literal["auto", "ids", "symbols", "names"] = "auto",
    ) -> dict[str, Any]:
        q = query.strip()
        if not q:
            raise ValueError("query is required.")
        vs = vs_currency.lower()
        slug = q.lower().replace(" ", "-")
        attempts: list[tuple[str, dict[str, str]]] = []
        if lookup in {"auto", "ids"}:
            attempts.append(("ids", {"ids": slug}))
        if lookup in {"auto", "symbols"}:
            attempts.append(("symbols", {"symbols": q.lower(), "include_tokens": "top"}))
        if lookup in {"auto", "names"}:
            attempts.append(("names", {"names": q}))

        last_error: str | None = None
        for matched_by, extra in attempts:
            params = {
                "vs_currency": vs,
                "order": "market_cap_desc",
                "per_page": "10",
                "page": "1",
                "sparkline": "false",
                "price_change_percentage": "1h,24h,7d,30d",
                **extra,
            }
            try:
                data = await self._client.get("/coins/markets", params)
            except RateLimitedError:
                raise  # surface rate limiting instead of returning empty results
            except UpstreamAPIError as exc:
                last_error = str(exc)
                continue
            if isinstance(data, list) and data:
                return {
                    "source": "coingecko",
                    "plan": "demo",
                    "endpoint": "/coins/markets",
                    "matched_by": matched_by,
                    "query": q,
                    "vs_currency": vs,
                    "results": data,
                }
        return {
            "source": "coingecko",
            "plan": "demo",
            "endpoint": "/coins/markets",
            "query": q,
            "vs_currency": vs,
            "results": [],
            "error": last_error,
        }

    async def coin_markets(
        self,
        vs_currency: str = "usd",
        ids: str | None = None,
        symbols: str | None = None,
        category: str | None = None,
        order: Order = "market_cap_desc",
        per_page: int = 20,
        page: int = 1,
    ) -> dict[str, Any]:
        params = {
            "vs_currency": vs_currency.lower(),
            "ids": ids,
            "symbols": symbols,
            "include_tokens": "top" if symbols else None,
            "category": category,
            "order": order,
            "per_page": _clamp(per_page, 1, 250),
            "page": max(page, 1),
            "sparkline": "false",
            "price_change_percentage": "1h,24h,7d,30d",
        }
        data = await self._client.get("/coins/markets", params)
        return base_response("/coins/markets", data, params)

    async def coin_details(self, coin_id: str) -> dict[str, Any]:
        cid = coin_id.strip().lower()
        if not cid:
            raise ValueError("coin_id is required.")
        params = {
            "localization": "false",
            "tickers": "false",
            "market_data": "true",
            "community_data": "false",
            "developer_data": "false",
            "sparkline": "false",
        }
        endpoint = f"/coins/{_seg(cid)}"
        data = await self._client.get(endpoint, params)
        return base_response(endpoint, data, params)

    async def top_movers(
        self,
        vs_currency: str = "usd",
        duration: Duration = "24h",
        top_coins: Literal["300", "500", "1000", "all"] = "1000",
    ) -> dict[str, Any]:
        vs = vs_currency.lower()
        params = {"vs_currency": vs, "duration": duration, "top_coins": top_coins}
        try:
            data = await self._client.get("/coins/top_gainers_losers", params)
            return base_response("/coins/top_gainers_losers", data, params)
        except UpstreamAPIError as exc:
            if exc.status_code not in {401, 403}:
                raise

        # Demo-safe fallback: derive movers from /coins/markets. That endpoint does not
        # accept every duration (e.g. 60d), so map unsupported windows to the closest one.
        window = duration if duration in _MARKETS_CHANGE_WINDOWS else "30d"
        fallback_params = {
            "vs_currency": vs,
            "order": "market_cap_desc",
            "per_page": "250",
            "page": "1",
            "sparkline": "false",
            "price_change_percentage": window,
        }
        markets = await self._client.get("/coins/markets", fallback_params)
        change_key = (
            "price_change_percentage_24h"
            if window == "24h"
            else f"price_change_percentage_{window}_in_currency"
        )
        sortable = [
            coin
            for coin in markets
            if isinstance(coin, dict) and isinstance(coin.get(change_key), int | float)
        ]
        gainers = sorted(sortable, key=lambda c: c[change_key], reverse=True)[:30]
        losers = sorted(sortable, key=lambda c: c[change_key])[:30]
        return {
            "source": "coingecko",
            "plan": "demo",
            "endpoint": "/coins/markets",
            "fallback_for": "/coins/top_gainers_losers",
            "params": fallback_params,
            "requested_duration": duration,
            "fallback_window": window,
            "sorted_by": change_key,
            "data": {"top_gainers": gainers, "top_losers": losers},
        }

    async def coin_market_chart(
        self,
        coin_id: str,
        days: Days = "7",
        vs_currency: str = "usd",
        interval: Literal["daily", "hourly"] | None = None,
        max_points: int = 80,
    ) -> dict[str, Any]:
        cid = coin_id.strip().lower()
        if not cid:
            raise ValueError("coin_id is required.")
        params = {"vs_currency": vs_currency.lower(), "days": days, "interval": interval}
        endpoint = f"/coins/{_seg(cid)}/market_chart"
        data = await self._client.get(endpoint, params)
        sampled = sample_chart(data, _clamp(max_points, 10, 250))
        return base_response(endpoint, sampled, params)

    async def coin_ohlc(
        self,
        coin_id: str,
        days: Days = "7",
        vs_currency: str = "usd",
        interval: Literal["daily", "hourly"] | None = None,
        max_candles: int = 80,
    ) -> dict[str, Any]:
        cid = coin_id.strip().lower()
        if not cid:
            raise ValueError("coin_id is required.")
        params = {"vs_currency": vs_currency.lower(), "days": days, "interval": interval}
        endpoint = f"/coins/{_seg(cid)}/ohlc"
        data = await self._client.get(endpoint, params)
        sampled = sample_points(data, _clamp(max_candles, 10, 250))
        return base_response(endpoint, sampled, params)

    async def token_price_by_contract(
        self,
        asset_platform_id: str,
        contract_addresses: str,
        vs_currencies: str = "usd",
    ) -> dict[str, Any]:
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
        endpoint = f"/simple/token_price/{_seg(platform)}"
        data = await self._client.get(endpoint, params)
        return base_response(endpoint, data, params)

    async def token_details_by_contract(
        self, asset_platform_id: str, contract_address: str
    ) -> dict[str, Any]:
        platform = asset_platform_id.strip().lower()
        address = contract_address.strip()
        if not platform or not address:
            raise ValueError("asset_platform_id and contract_address are required.")
        endpoint = f"/coins/{_seg(platform)}/contract/{_seg(address)}"
        data = await self._client.get(endpoint)
        return base_response(endpoint, data)

    async def global_market(self) -> dict[str, Any]:
        data = await self._client.get("/global")
        return base_response("/global", data)

    async def defi_market(self) -> dict[str, Any]:
        data = await self._client.get("/global/decentralized_finance_defi")
        return base_response("/global/decentralized_finance_defi", data)

    async def categories(
        self,
        order: Literal[
            "market_cap_desc",
            "market_cap_asc",
            "name_desc",
            "name_asc",
            "market_cap_change_24h_desc",
            "market_cap_change_24h_asc",
        ] = "market_cap_desc",
    ) -> dict[str, Any]:
        params = {"order": order}
        data = await self._client.get("/coins/categories", params)
        return base_response("/coins/categories", data, params)

    async def exchanges(self, per_page: int = 20, page: int = 1) -> dict[str, Any]:
        params = {"per_page": _clamp(per_page, 1, 250), "page": max(page, 1)}
        data = await self._client.get("/exchanges", params)
        return base_response("/exchanges", data, params)

    async def exchange_tickers(
        self, exchange_id: str, coin_ids: str | None = None, page: int = 1
    ) -> dict[str, Any]:
        eid = exchange_id.strip().lower()
        if not eid:
            raise ValueError("exchange_id is required.")
        params = {
            "coin_ids": coin_ids,
            "page": max(page, 1),
            "order": "trust_score_desc",
            "include_exchange_logo": "true",
            "depth": "false",
        }
        endpoint = f"/exchanges/{_seg(eid)}/tickers"
        data = await self._client.get(endpoint, params)
        return base_response(endpoint, data, params)

    async def exchange_rates(self) -> dict[str, Any]:
        data = await self._client.get("/exchange_rates")
        return base_response("/exchange_rates", data)

    async def nft_details(self, nft_id: str) -> dict[str, Any]:
        nid = nft_id.strip().lower()
        if not nid:
            raise ValueError("nft_id is required.")
        endpoint = f"/nfts/{_seg(nid)}"
        data = await self._client.get(endpoint)
        return base_response(endpoint, data)


_service: CoinGeckoService | None = None


def get_coingecko_service() -> CoinGeckoService:
    global _service
    if _service is None:
        _service = CoinGeckoService()
    return _service
