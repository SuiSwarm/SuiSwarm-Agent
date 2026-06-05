"""Transport client for the CoinGecko Demo API.

Also serves GeckoTerminal on-chain DEX data, which CoinGecko exposes under the
``/onchain`` namespace using the same Demo API key. Built on the shared resilient
:class:`AsyncHttpClient` (retry / backoff / rate-limit / cache).
"""

from __future__ import annotations

from typing import Any

from suiswarm_agent.config.settings import Settings, get_settings
from suiswarm_agent.core.constants import USER_AGENT
from suiswarm_agent.core.exceptions import ConfigError
from suiswarm_agent.infra.http.client import AsyncHttpClient


class CoinGeckoClient:
    """Thin async client over the CoinGecko Demo API surface."""

    def __init__(self, settings: Settings | None = None) -> None:
        settings = settings or get_settings()
        self._cfg = settings.coingecko
        headers = {"User-Agent": USER_AGENT}
        if self._cfg.demo_api_key is not None:
            headers["x-cg-demo-api-key"] = self._cfg.demo_api_key.get_secret_value()
        self._http = AsyncHttpClient(
            self._cfg.base_url,
            default_headers=headers,
            settings=settings.http,
            service_name="coingecko",
        )

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        if not self._cfg.enabled:
            raise ConfigError(
                "Missing COINGECKO_DEMO_API_KEY. Add your CoinGecko Demo API key to .env."
            )
        return await self._http.get_json(path, params, use_cache=True)

    async def aclose(self) -> None:
        await self._http.aclose()


_client: CoinGeckoClient | None = None


def get_coingecko_client() -> CoinGeckoClient:
    """Process-wide CoinGecko client singleton."""
    global _client
    if _client is None:
        _client = CoinGeckoClient()
    return _client


async def aclose_coingecko_client() -> None:
    """Close and reset the singleton (call on app/CLI shutdown to release pools)."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
