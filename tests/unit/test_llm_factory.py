"""LLM factory: requires a key, builds a provider-agnostic model."""

from __future__ import annotations

import pytest
from langchain_core.language_models import BaseChatModel
from pydantic import SecretStr

from suiswarm_agent.core.exceptions import ConfigError
from suiswarm_agent.llm import factory


def test_requires_api_key(monkeypatch: pytest.MonkeyPatch, make_settings) -> None:
    settings = make_settings()
    settings.llm.api_key = None
    monkeypatch.setattr(factory, "get_settings", lambda: settings)
    with pytest.raises(ConfigError):
        factory.get_chat_model()


def test_builds_chat_model(monkeypatch: pytest.MonkeyPatch, make_settings) -> None:
    settings = make_settings()
    settings.llm.api_key = SecretStr("sk-test")
    monkeypatch.setattr(factory, "get_settings", lambda: settings)
    model = factory.get_chat_model("worker")
    assert isinstance(model, BaseChatModel)
