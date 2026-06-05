"""A shared, resilient async HTTP client.

Features:
* connection pooling (one ``httpx.AsyncClient`` reused per event loop),
* retry with exponential backoff on transient failures (429 / 5xx / transport),
* a simple per-client rate limiter (CoinGecko demo tier is strict),
* an optional short-TTL response cache for idempotent GETs,
* mapping of HTTP/transport failures to the domain exception hierarchy.

Used by every service client (CoinGecko, GeckoTerminal, the Sui NestJS service).
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from suiswarm_agent.config.settings import HTTPSettings, get_settings
from suiswarm_agent.core.exceptions import RateLimitedError, UpstreamAPIError
from suiswarm_agent.core.logging import get_logger

logger = get_logger(__name__)

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class _RetryableHTTPError(Exception):
    """Internal marker so tenacity retries only transient HTTP responses."""

    def __init__(self, response: httpx.Response):
        self.response = response
        super().__init__(f"retryable status {response.status_code}")


class AsyncRateLimiter:
    """Minimal async rate limiter enforcing a minimum interval between calls."""

    def __init__(self, per_minute: int) -> None:
        self._min_interval = 60.0 / per_minute if per_minute > 0 else 0.0
        self._last = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        if self._min_interval <= 0:
            return
        async with self._lock:
            wait = self._last + self._min_interval - time.monotonic()
            if wait > 0:
                await asyncio.sleep(wait)
            self._last = time.monotonic()


class AsyncHttpClient:
    """Resilient async HTTP client bound to a single upstream base URL."""

    def __init__(
        self,
        base_url: str,
        *,
        default_headers: dict[str, str] | None = None,
        settings: HTTPSettings | None = None,
        service_name: str = "upstream",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.default_headers = default_headers or {}
        self.settings = settings or get_settings().http
        self.service_name = service_name
        self._limiter = AsyncRateLimiter(self.settings.rate_limit_per_minute)
        self._cache: dict[str, tuple[float, Any]] = {}
        self._http: httpx.AsyncClient | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    # -- lifecycle ----------------------------------------------------------
    def _client(self) -> httpx.AsyncClient:
        """Return an ``httpx.AsyncClient`` valid for the current running loop."""
        loop = asyncio.get_running_loop()
        if self._http is None or self._http.is_closed or self._loop is not loop:
            limits = httpx.Limits(max_connections=self.settings.max_connections)
            self._http = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self.default_headers,
                timeout=self.settings.timeout,
                limits=limits,
            )
            self._loop = loop
        return self._http

    async def aclose(self) -> None:
        if self._http is not None and not self._http.is_closed:
            await self._http.aclose()
        self._http = None

    # -- requests -----------------------------------------------------------
    async def get_json(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        headers: dict[str, str] | None = None,
        use_cache: bool = True,
    ) -> Any:
        return await self.request_json(
            "GET", path, params=params, headers=headers, use_cache=use_cache
        )

    async def post_json(
        self,
        path: str,
        json: Any = None,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        return await self.request_json("POST", path, params=params, json=json, headers=headers)

    async def request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        headers: dict[str, str] | None = None,
        use_cache: bool = False,
    ) -> Any:
        """Perform a request with retry + rate-limit, returning parsed JSON."""
        clean_params = {k: v for k, v in (params or {}).items() if v is not None}
        cache_key = ""
        ttl = self.settings.cache_ttl_seconds
        if use_cache and method == "GET" and ttl > 0:
            cache_key = f"{path}?{sorted(clean_params.items())}"
            cached = self._cache.get(cache_key)
            if cached and cached[0] > time.monotonic():
                return cached[1]

        async def _do() -> httpx.Response:
            await self._limiter.acquire()
            response = await self._client().request(
                method, path, params=clean_params, json=json, headers=headers
            )
            if response.status_code in _RETRYABLE_STATUS:
                raise _RetryableHTTPError(response)
            return response

        response = await self._with_retry(_do, path)

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            self._raise_for_status(exc)

        data = response.json()
        if cache_key and ttl > 0:
            self._cache[cache_key] = (time.monotonic() + ttl, data)
        return data

    # -- internals ----------------------------------------------------------
    async def _with_retry(self, func: Any, path: str) -> httpx.Response:
        def _is_retryable(exc: BaseException) -> bool:
            return isinstance(
                exc, _RetryableHTTPError | httpx.TransportError | httpx.TimeoutException
            )

        last_response: httpx.Response | None = None
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self.settings.max_retries + 1),
                wait=wait_exponential(
                    multiplier=self.settings.backoff_base, max=self.settings.backoff_max
                ),
                retry=retry_if_exception(_is_retryable),
                reraise=True,
            ):
                with attempt:
                    try:
                        return await func()
                    except _RetryableHTTPError as exc:
                        last_response = exc.response
                        logger.warning(
                            "http.retry service=%s path=%s status=%s attempt=%s",
                            self.service_name,
                            path,
                            exc.response.status_code,
                            attempt.retry_state.attempt_number,
                        )
                        raise
        except _RetryableHTTPError as exc:
            last_response = exc.response
        except (httpx.TransportError, httpx.TimeoutException) as exc:
            raise UpstreamAPIError(
                f"{self.service_name} request failed (network).",
                detail=type(exc).__name__,
            ) from exc

        # Retries exhausted on a retryable status code.
        assert last_response is not None
        if last_response.status_code == 429:
            raise RateLimitedError(
                f"{self.service_name} rate limit exceeded.",
                status_code=429,
                detail="too many requests",
            )
        raise UpstreamAPIError(
            f"{self.service_name} returned {last_response.status_code}.",
            status_code=last_response.status_code,
            detail="server error",
        )

    def _raise_for_status(self, exc: httpx.HTTPStatusError) -> None:
        status = exc.response.status_code
        # Keep upstream bodies out of user-facing messages; log them instead.
        logger.warning(
            "http.error service=%s status=%s body=%s",
            self.service_name,
            status,
            exc.response.text[:500],
        )
        if status == 429:
            raise RateLimitedError(
                f"{self.service_name} rate limit exceeded.", status_code=status
            ) from exc
        detail = "client error" if 400 <= status < 500 else "server error"
        raise UpstreamAPIError(
            f"{self.service_name} returned HTTP {status}.", status_code=status, detail=detail
        ) from exc
