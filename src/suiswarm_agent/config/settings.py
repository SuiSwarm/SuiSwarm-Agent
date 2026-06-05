"""Typed, nested application configuration (single source of truth).

Design notes
------------
* Structured config uses the nested-delimiter form, e.g. ``LLM__MODEL``,
  ``HTTP__TIMEOUT``, ``SUI_SERVICE__BASE_URL``.
* Conventional secret env names (``OPENAI_API_KEY``, ``TAVILY_API_KEY``,
  ``COINGECKO_DEMO_API_KEY``, ``LANGFUSE_*``) are read via top-level alias fields and
  then *bridged* into the relevant nested model. pydantic-settings does not apply
  ``validation_alias`` to nested-model fields, hence the explicit bridge.
* No other module reads ``os.environ`` directly — everything goes through
  :func:`get_settings`.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from dotenv import load_dotenv
from pydantic import AliasChoices, BaseModel, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# ---------------------------------------------------------------------------
# Nested sections
# ---------------------------------------------------------------------------
class LLMSettings(BaseModel):
    """Provider-agnostic chat-model configuration (see ``llm/factory.py``)."""

    provider: str = "openai"
    model: str = "gpt-4o-mini"
    api_key: SecretStr | None = None
    base_url: str | None = None  # for Azure/OpenAI-compatible/local endpoints
    # Per-role temperatures. Routing should be deterministic; workers a bit creative.
    temperature_supervisor: float = 0.0
    temperature_worker: float = 0.2
    temperature_default: float = 0.3
    request_timeout: float = 60.0
    max_retries: int = 2

    @model_validator(mode="after")
    def _normalize_model(self) -> LLMSettings:
        # Accept "openai/gpt-4o-mini" style and strip the provider prefix.
        if "/" in self.model:
            prefix, _, rest = self.model.partition("/")
            if prefix == self.provider:
                self.model = rest
        return self


class CoinGeckoSettings(BaseModel):
    """CoinGecko Demo API. Also serves GeckoTerminal on-chain data under ``/onchain``."""

    demo_api_key: SecretStr | None = None
    base_url: str = "https://api.coingecko.com/api/v3"

    @property
    def enabled(self) -> bool:
        return self.demo_api_key is not None


class TavilySettings(BaseModel):
    """Tavily web search configuration."""

    api_key: SecretStr | None = None
    max_results: int = 5
    search_depth: Literal["basic", "advanced"] = "basic"
    topic: Literal["general", "news"] = "general"
    include_answer: bool = True

    @property
    def enabled(self) -> bool:
        return self.api_key is not None


class SuiServiceSettings(BaseModel):
    """Client config for the external NestJS Sui service (D5).

    The agent never talks to Sui RPC directly; it calls this service over REST.
    """

    base_url: str | None = None
    api_key: SecretStr | None = None
    api_key_header: str = "x-api-key"
    timeout: float = 30.0
    # D6: the agent has full read+write access by default; the policy-contract repo is the
    # guardrail. Operators may still restrict the agent to read-only (GET) here if desired.
    allow_writes: bool = True

    @property
    def enabled(self) -> bool:
        return self.base_url is not None


class LangfuseSettings(BaseModel):
    """Langfuse 4.x tracing configuration (optional)."""

    public_key: SecretStr | None = None
    secret_key: SecretStr | None = None
    host: str = "https://cloud.langfuse.com"

    @property
    def enabled(self) -> bool:
        return self.public_key is not None and self.secret_key is not None


class HTTPSettings(BaseModel):
    """Shared async HTTP client behavior (retry / rate-limit / cache)."""

    timeout: float = 20.0
    max_retries: int = 3
    backoff_base: float = 0.5
    backoff_max: float = 8.0
    rate_limit_per_minute: int = 30  # CoinGecko demo tier is strict
    cache_ttl_seconds: float = 0.0  # 0 disables caching
    max_connections: int = 20


class AgentSettings(BaseModel):
    """Swarm / conversation behavior."""

    max_conversation_messages: int = 100
    recursion_limit: int = 40
    supervisor_output_mode: Literal["full_history", "last_message"] = "last_message"
    # Comma-tolerant list of enabled sub-agents; "sui" is added automatically when the
    # Sui service is configured. Market + research are the v1 defaults.
    enabled_agents: list[str] = Field(default_factory=lambda: ["market", "research"])


class PersistenceSettings(BaseModel):
    """LangGraph checkpointer backend."""

    backend: Literal["memory", "sqlite", "postgres"] = "memory"
    sqlite_path: str = "./.suiswarm/checkpoints.sqlite"
    postgres_dsn: str | None = None


class ServerSettings(BaseModel):
    """FastAPI / uvicorn settings (API surface)."""

    host: str = "0.0.0.0"
    port: int = 8000
    # Empty = no cross-origin access (safe default). Set explicit origins to enable CORS;
    # never combine "*" with credentials (the CORS spec forbids it).
    cors_origins: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Root settings
# ---------------------------------------------------------------------------
class Settings(BaseSettings):
    """Root application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False,
    )

    llm: LLMSettings = Field(default_factory=LLMSettings)
    coingecko: CoinGeckoSettings = Field(default_factory=CoinGeckoSettings)
    tavily: TavilySettings = Field(default_factory=TavilySettings)
    sui_service: SuiServiceSettings = Field(default_factory=SuiServiceSettings)
    langfuse: LangfuseSettings = Field(default_factory=LangfuseSettings)
    http: HTTPSettings = Field(default_factory=HTTPSettings)
    agent: AgentSettings = Field(default_factory=AgentSettings)
    persistence: PersistenceSettings = Field(default_factory=PersistenceSettings)
    server: ServerSettings = Field(default_factory=ServerSettings)

    # --- conventional secret aliases (sources only; bridged into nested models) ---
    openai_api_key: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("OPENAI_API_KEY")
    )
    tavily_api_key: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("TAVILY_API_KEY")
    )
    coingecko_demo_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("COINGECKO_DEMO_API_KEY", "COINGECKO_API_KEY"),
    )
    langfuse_public_key: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("LANGFUSE_PUBLIC_KEY")
    )
    langfuse_secret_key: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("LANGFUSE_SECRET_KEY")
    )
    langfuse_host: str | None = Field(
        default=None, validation_alias=AliasChoices("LANGFUSE_BASE_URL", "LANGFUSE_HOST")
    )

    @model_validator(mode="after")
    def _bridge_conventional_secrets(self) -> Settings:
        self.llm.api_key = self.llm.api_key or self.openai_api_key
        self.coingecko.demo_api_key = self.coingecko.demo_api_key or self.coingecko_demo_api_key
        self.tavily.api_key = self.tavily.api_key or self.tavily_api_key
        self.langfuse.public_key = self.langfuse.public_key or self.langfuse_public_key
        self.langfuse.secret_key = self.langfuse.secret_key or self.langfuse_secret_key
        if self.langfuse_host:
            self.langfuse.host = self.langfuse_host
        return self

    def capabilities(self) -> dict[str, bool]:
        """Map of optional capability -> enabled, for ``suiswarm config check``."""
        return {
            "llm": self.llm.api_key is not None,
            "coingecko": self.coingecko.enabled,
            "tavily": self.tavily.enabled,
            "sui_service": self.sui_service.enabled,
            "langfuse": self.langfuse.enabled,
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings singleton (loads ``.env`` once)."""
    load_dotenv()
    return Settings()
