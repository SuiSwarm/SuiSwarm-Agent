"""Shared pytest fixtures.

Tests run offline: HTTP is mocked with ``respx`` and the LLM is never invoked. An
autouse fixture provides a dummy ``OPENAI_API_KEY`` and resets the settings cache so
tests are deterministic regardless of the host environment.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from suiswarm_agent.config.settings import HTTPSettings, Settings, get_settings


@pytest.fixture(autouse=True)
def _isolated_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy")
    # Avoid host creds leaking into tests that assert "disabled" capabilities.
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.delenv("COINGECKO_DEMO_API_KEY", raising=False)
    monkeypatch.delenv("COINGECKO_API_KEY", raising=False)
    monkeypatch.delenv("SUI_SERVICE__BASE_URL", raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def fast_http() -> Callable[..., HTTPSettings]:
    """Factory for HTTP settings with retries/rate-limit that don't sleep."""

    def _make(**overrides: object) -> HTTPSettings:
        params: dict = {"rate_limit_per_minute": 0, "backoff_base": 0.0, "backoff_max": 0.0}
        params.update(overrides)
        return HTTPSettings(**params)

    return _make


@pytest.fixture
def make_settings(fast_http: Callable[..., HTTPSettings]) -> Callable[..., Settings]:
    """Factory for Settings with sleep-free HTTP by default."""

    def _make(**overrides: object) -> Settings:
        params: dict = {"http": fast_http()}
        params.update(overrides)
        # Ignore any host .env so tests are deterministic.
        return Settings(_env_file=None, **params)

    return _make
