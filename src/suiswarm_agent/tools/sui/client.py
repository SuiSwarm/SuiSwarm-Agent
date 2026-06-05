"""HTTP client for the external NestJS Sui service (D5).

The agent never speaks Sui RPC directly. All Sui interaction (RPC, key custody, tx
signing) lives in a separate NestJS service; this client calls its REST API. Auth is an
API key sent in a configurable header.
"""

from __future__ import annotations

from typing import Any

from suiswarm_agent.config.settings import Settings, get_settings
from suiswarm_agent.core.constants import USER_AGENT
from suiswarm_agent.core.exceptions import ConfigError, SuiServiceError, UpstreamAPIError
from suiswarm_agent.infra.http.client import AsyncHttpClient

_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class SuiServiceClient:
    """Async REST client for the NestJS Sui service."""

    def __init__(self, settings: Settings | None = None) -> None:
        settings = settings or get_settings()
        self._cfg = settings.sui_service
        headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
        if self._cfg.api_key is not None:
            headers[self._cfg.api_key_header] = self._cfg.api_key.get_secret_value()
        # http timeout for this service may differ from the global default.
        http_settings = settings.http.model_copy(update={"timeout": self._cfg.timeout})
        base_url = self._cfg.base_url or "http://localhost:0"
        self._http = AsyncHttpClient(
            base_url,
            default_headers=headers,
            settings=http_settings,
            service_name="sui-service",
        )

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
    ) -> Any:
        if not self._cfg.enabled:
            raise ConfigError(
                "Sui service is not configured. Set SUI_SERVICE__BASE_URL (and API key)."
            )
        if method.upper() in _WRITE_METHODS and not self._cfg.allow_writes:
            raise ConfigError(
                "Sui write operations are disabled (set SUI_SERVICE__ALLOW_WRITES=true to enable)."
            )
        if not path.startswith("/"):
            path = "/" + path
        try:
            return await self._http.request_json(method.upper(), path, params=params, json=json)
        except UpstreamAPIError as exc:
            raise SuiServiceError(
                f"Sui service call failed: {exc}",
                status_code=exc.status_code,
                detail=exc.detail,
            ) from exc

    async def aclose(self) -> None:
        await self._http.aclose()


_client: SuiServiceClient | None = None


def get_sui_client() -> SuiServiceClient:
    global _client
    if _client is None:
        _client = SuiServiceClient()
    return _client


async def aclose_sui_client() -> None:
    """Close and reset the singleton (call on app/CLI shutdown to release pools)."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
