"""GeckoTerminal on-chain domain logic (async).

GeckoTerminal data is reachable through CoinGecko's ``/onchain`` namespace using the
same Demo API key, so this service reuses :class:`CoinGeckoClient`.
"""

from __future__ import annotations

from typing import Any, Literal
from urllib.parse import quote

from suiswarm_agent.tools.market.coingecko.client import CoinGeckoClient, get_coingecko_client
from suiswarm_agent.tools.market.coingecko.models import base_response


def _seg(value: str) -> str:
    return quote(value.strip(), safe="")


class GeckoTerminalService:
    def __init__(self, client: CoinGeckoClient | None = None) -> None:
        self._client = client or get_coingecko_client()

    def _resp(
        self, endpoint: str, data: Any, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return base_response(endpoint, data, params, source="geckoterminal")

    async def networks(self, page: int = 1) -> dict[str, Any]:
        params = {"page": max(page, 1)}
        data = await self._client.get("/onchain/networks", params)
        return self._resp("/onchain/networks", data, params)

    async def dexes(self, network: str, page: int = 1) -> dict[str, Any]:
        nid = network.strip().lower()
        if not nid:
            raise ValueError("network is required.")
        params = {"page": max(page, 1)}
        endpoint = f"/onchain/networks/{_seg(nid)}/dexes"
        data = await self._client.get(endpoint, params)
        return self._resp(endpoint, data, params)

    async def onchain_token_price(self, network: str, addresses: str) -> dict[str, Any]:
        nid = network.strip().lower()
        addrs = addresses.strip()
        if not nid or not addrs:
            raise ValueError("network and addresses are required.")
        params = {
            "include_market_cap": "true",
            "mcap_fdv_fallback": "true",
            "include_24hr_vol": "true",
            "include_24hr_price_change": "true",
            "include_total_reserve_in_usd": "true",
            "include_inactive_source": "true",
        }
        endpoint = f"/onchain/simple/networks/{_seg(nid)}/token_price/{_seg(addrs)}"
        data = await self._client.get(endpoint, params)
        return self._resp(endpoint, data, params)

    async def onchain_token_info(self, network: str, address: str) -> dict[str, Any]:
        nid = network.strip().lower()
        addr = address.strip()
        if not nid or not addr:
            raise ValueError("network and address are required.")
        endpoint = f"/onchain/networks/{_seg(nid)}/tokens/{_seg(addr)}/info"
        data = await self._client.get(endpoint)
        return self._resp(endpoint, data)

    async def token_top_pools(
        self, network: str, token_address: str, page: int = 1
    ) -> dict[str, Any]:
        nid = network.strip().lower()
        addr = token_address.strip()
        if not nid or not addr:
            raise ValueError("network and token_address are required.")
        params = {
            "include": "base_token,quote_token,dex",
            "page": max(page, 1),
            "sort": "h24_volume_usd_liquidity_desc",
            "include_inactive_source": "true",
        }
        endpoint = f"/onchain/networks/{_seg(nid)}/tokens/{_seg(addr)}/pools"
        data = await self._client.get(endpoint, params)
        return self._resp(endpoint, data, params)

    async def trending_pools(
        self,
        network: str | None = None,
        duration: Literal["5m", "1h", "6h", "24h"] = "24h",
        page: int = 1,
    ) -> dict[str, Any]:
        nid = network.strip().lower() if network else None
        if nid:
            endpoint = f"/onchain/networks/{_seg(nid)}/trending_pools"
            include = "base_token,quote_token,dex"
        else:
            endpoint = "/onchain/networks/trending_pools"
            include = "base_token,quote_token,dex,network"
        params = {"include": include, "duration": duration, "page": max(page, 1)}
        data = await self._client.get(endpoint, params)
        return self._resp(endpoint, data, params)

    async def new_pools(self, network: str | None = None, page: int = 1) -> dict[str, Any]:
        nid = network.strip().lower() if network else None
        if nid:
            endpoint = f"/onchain/networks/{_seg(nid)}/new_pools"
            include = "base_token,quote_token,dex"
        else:
            endpoint = "/onchain/networks/new_pools"
            include = "base_token,quote_token,dex,network"
        params = {"include": include, "page": max(page, 1)}
        data = await self._client.get(endpoint, params)
        return self._resp(endpoint, data, params)

    async def search_pools(
        self, query: str, network: str | None = None, page: int = 1
    ) -> dict[str, Any]:
        q = query.strip()
        if not q:
            raise ValueError("query is required.")
        params = {
            "query": q,
            "network": network.strip().lower() if network else None,
            "include": "base_token,quote_token,dex",
            "page": max(page, 1),
        }
        data = await self._client.get("/onchain/search/pools", params)
        return self._resp("/onchain/search/pools", data, params)


_service: GeckoTerminalService | None = None


def get_geckoterminal_service() -> GeckoTerminalService:
    global _service
    if _service is None:
        _service = GeckoTerminalService()
    return _service
