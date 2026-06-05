"""Settings: conventional-alias bridging, nested env, normalization, capabilities."""

from __future__ import annotations

import pytest

from suiswarm_agent.config.settings import LLMSettings, Settings


def test_conventional_secret_aliases_bridge_into_nested(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-conventional")
    monkeypatch.setenv("COINGECKO_DEMO_API_KEY", "cg-demo")
    settings = Settings()
    assert settings.llm.api_key is not None
    assert settings.llm.api_key.get_secret_value() == "sk-conventional"
    assert settings.coingecko.demo_api_key is not None
    assert settings.coingecko.demo_api_key.get_secret_value() == "cg-demo"


def test_nested_delimiter_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM__MODEL", "gpt-4o")
    monkeypatch.setenv("HTTP__TIMEOUT", "33")
    monkeypatch.setenv("SUI_SERVICE__BASE_URL", "http://nest:3000")
    settings = Settings()
    assert settings.llm.model == "gpt-4o"
    assert settings.http.timeout == 33.0
    assert settings.sui_service.enabled


def test_model_provider_prefix_is_stripped() -> None:
    assert LLMSettings(provider="openai", model="openai/gpt-4o-mini").model == "gpt-4o-mini"


def test_capabilities_reflect_configuration(make_settings) -> None:
    caps = make_settings().capabilities()
    # dummy OPENAI key from the autouse fixture -> llm enabled; the rest are cleared.
    assert caps["llm"] is True
    assert caps["coingecko"] is False
    assert caps["sui_service"] is False
