"""Resilient HTTP client: retry, error mapping, rate-limit no-op."""

from __future__ import annotations

import httpx
import pytest
import respx

from suiswarm_agent.core.exceptions import RateLimitedError, UpstreamAPIError
from suiswarm_agent.infra.http.client import AsyncHttpClient


@respx.mock
async def test_retry_then_success(fast_http) -> None:
    route = respx.get("https://svc.test/ping").mock(
        side_effect=[httpx.Response(503), httpx.Response(200, json={"ok": True})]
    )
    client = AsyncHttpClient(
        "https://svc.test", settings=fast_http(max_retries=3), service_name="svc"
    )
    assert await client.get_json("/ping") == {"ok": True}
    assert route.call_count == 2


@respx.mock
async def test_client_error_maps_to_upstream_error(fast_http) -> None:
    respx.get("https://svc.test/missing").mock(return_value=httpx.Response(404, json={}))
    client = AsyncHttpClient(
        "https://svc.test", settings=fast_http(max_retries=1), service_name="svc"
    )
    with pytest.raises(UpstreamAPIError) as exc_info:
        await client.get_json("/missing")
    assert exc_info.value.status_code == 404


@respx.mock
async def test_429_exhausts_to_rate_limited(fast_http) -> None:
    route = respx.get("https://svc.test/rl").mock(return_value=httpx.Response(429))
    client = AsyncHttpClient(
        "https://svc.test", settings=fast_http(max_retries=2), service_name="svc"
    )
    with pytest.raises(RateLimitedError):
        await client.get_json("/rl")
    assert route.call_count == 3  # initial + 2 retries


@respx.mock
async def test_none_params_are_dropped(fast_http) -> None:
    route = respx.get("https://svc.test/q").mock(return_value=httpx.Response(200, json={}))
    client = AsyncHttpClient("https://svc.test", settings=fast_http(), service_name="svc")
    await client.get_json("/q", {"a": "1", "b": None})
    assert route.calls.last.request.url.params.get("a") == "1"
    assert "b" not in route.calls.last.request.url.params
