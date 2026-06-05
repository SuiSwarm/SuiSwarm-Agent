"""CoinGecko service: envelope shape, demo-safe top-movers fallback."""

from __future__ import annotations

import httpx
import pytest
import respx

from suiswarm_agent.config.settings import CoinGeckoSettings
from suiswarm_agent.core.exceptions import RateLimitedError
from suiswarm_agent.tools.market.coingecko.client import CoinGeckoClient
from suiswarm_agent.tools.market.coingecko.service import CoinGeckoService

BASE = "https://api.coingecko.com/api/v3"


def _service(make_settings) -> CoinGeckoService:
    settings = make_settings(coingecko=CoinGeckoSettings(demo_api_key="test-key"))
    return CoinGeckoService(CoinGeckoClient(settings))


@respx.mock
async def test_search_wraps_in_envelope(make_settings) -> None:
    respx.get(f"{BASE}/search").mock(
        return_value=httpx.Response(200, json={"coins": [{"id": "bitcoin"}]})
    )
    out = await _service(make_settings).search("bitcoin")
    assert out["source"] == "coingecko"
    assert out["endpoint"] == "/search"
    assert out["data"]["coins"][0]["id"] == "bitcoin"


@respx.mock
async def test_top_movers_falls_back_on_401(make_settings) -> None:
    respx.get(f"{BASE}/coins/top_gainers_losers").mock(return_value=httpx.Response(401, json={}))
    respx.get(f"{BASE}/coins/markets").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"id": "up", "price_change_percentage_24h": 5.0},
                {"id": "down", "price_change_percentage_24h": -3.0},
            ],
        )
    )
    out = await _service(make_settings).top_movers(duration="24h")
    assert out["fallback_for"] == "/coins/top_gainers_losers"
    assert out["data"]["top_gainers"][0]["id"] == "up"
    assert out["data"]["top_losers"][0]["id"] == "down"


@respx.mock
async def test_top_movers_60d_maps_to_supported_window(make_settings) -> None:
    # /coins/markets does not accept 60d; the fallback must use a supported window.
    respx.get(f"{BASE}/coins/top_gainers_losers").mock(return_value=httpx.Response(403, json={}))
    route = respx.get(f"{BASE}/coins/markets").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"id": "a", "price_change_percentage_30d_in_currency": 10.0},
                {"id": "b", "price_change_percentage_30d_in_currency": -5.0},
            ],
        )
    )
    out = await _service(make_settings).top_movers(duration="60d")
    assert out["requested_duration"] == "60d"
    assert out["fallback_window"] == "30d"
    assert route.calls.last.request.url.params.get("price_change_percentage") == "30d"
    assert out["data"]["top_gainers"][0]["id"] == "a"


@respx.mock
async def test_search_coin_market_reraises_rate_limit(make_settings) -> None:
    respx.get(f"{BASE}/coins/markets").mock(return_value=httpx.Response(429))
    with pytest.raises(RateLimitedError):
        await _service(make_settings).search_coin_market("btc")


@respx.mock
async def test_coin_id_is_url_encoded(make_settings) -> None:
    route = respx.get(url__startswith=f"{BASE}/coins/").mock(
        return_value=httpx.Response(200, json={"id": "x"})
    )
    await _service(make_settings).coin_details("weird id/with space")
    assert "weird%20id%2Fwith%20space" in str(route.calls.last.request.url)
