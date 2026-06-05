"""GeckoTerminal service: uses the CoinGecko /onchain namespace, geckoterminal source."""

from __future__ import annotations

import httpx
import respx

from suiswarm_agent.config.settings import CoinGeckoSettings
from suiswarm_agent.tools.market.coingecko.client import CoinGeckoClient
from suiswarm_agent.tools.market.geckoterminal.service import GeckoTerminalService

BASE = "https://api.coingecko.com/api/v3"


def _service(make_settings) -> GeckoTerminalService:
    settings = make_settings(coingecko=CoinGeckoSettings(demo_api_key="test-key"))
    return GeckoTerminalService(CoinGeckoClient(settings))


@respx.mock
async def test_networks_envelope_source(make_settings) -> None:
    respx.get(f"{BASE}/onchain/networks").mock(
        return_value=httpx.Response(200, json={"data": [{"id": "sui"}]})
    )
    out = await _service(make_settings).networks()
    assert out["source"] == "geckoterminal"
    assert out["endpoint"] == "/onchain/networks"


@respx.mock
async def test_trending_pools_global_includes_network(make_settings) -> None:
    route = respx.get(f"{BASE}/onchain/networks/trending_pools").mock(
        return_value=httpx.Response(200, json={"data": []})
    )
    await _service(make_settings).trending_pools()
    assert (
        route.calls.last.request.url.params.get("include") == "base_token,quote_token,dex,network"
    )
