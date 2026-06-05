"""Provider-agnostic chat-model factory.

Uses LangChain's ``init_chat_model`` so the provider (OpenAI / Anthropic / Azure /
local) is selected purely from configuration. Per-role temperatures let the
supervisor route deterministically while workers stay slightly creative.
"""

from __future__ import annotations

from typing import Any, Literal

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from suiswarm_agent.config.settings import get_settings
from suiswarm_agent.core.exceptions import ConfigError, LLMError
from suiswarm_agent.core.logging import get_logger

logger = get_logger(__name__)

Role = Literal["supervisor", "worker", "default"]


def _temperature_for(role: Role) -> float:
    llm = get_settings().llm
    return {
        "supervisor": llm.temperature_supervisor,
        "worker": llm.temperature_worker,
        "default": llm.temperature_default,
    }[role]


def get_chat_model(
    role: Role = "default",
    *,
    model: str | None = None,
    temperature: float | None = None,
    **overrides: Any,
) -> BaseChatModel:
    """Build a chat model for the given role from configuration.

    Raises :class:`ConfigError` if no API key is configured and :class:`LLMError`
    if the provider/model cannot be instantiated.
    """
    llm = get_settings().llm
    if llm.api_key is None:
        raise ConfigError(
            "No LLM API key configured. Set OPENAI_API_KEY (or LLM__API_KEY) in your .env."
        )

    kwargs: dict[str, Any] = {
        "model": model or llm.model,
        "model_provider": llm.provider,
        "temperature": temperature if temperature is not None else _temperature_for(role),
        "timeout": llm.request_timeout,
        "max_retries": llm.max_retries,
        "api_key": llm.api_key.get_secret_value(),
    }
    if llm.base_url:
        kwargs["base_url"] = llm.base_url
    kwargs.update(overrides)

    try:
        return init_chat_model(**kwargs)
    except Exception as exc:  # pragma: no cover - depends on provider/runtime
        raise LLMError(f"Failed to initialize chat model '{kwargs['model']}': {exc}") from exc
