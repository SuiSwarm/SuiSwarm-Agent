"""Domain exception hierarchy for SuiSwarm Agent.

All application errors derive from :class:`SuiSwarmError` so callers can catch the
whole family. User-facing surfaces (CLI/API) should render ``str(exc)`` only after
the message has been sanitized — never leak raw upstream payloads.
"""

from __future__ import annotations


class SuiSwarmError(Exception):
    """Base class for every SuiSwarm Agent error."""


class ConfigError(SuiSwarmError):
    """Raised when configuration is missing or invalid (e.g. no LLM API key)."""


class LLMError(SuiSwarmError):
    """Raised when building or invoking the chat model fails."""


class ToolError(SuiSwarmError):
    """Base class for tool-layer failures."""


class ToolNotFoundError(ToolError):
    """Raised when a requested tool is not registered."""


class ToolExecutionError(ToolError):
    """Raised when a tool fails during execution."""


class UpstreamAPIError(ToolError):
    """Raised when an upstream HTTP API returns an error response.

    ``status_code`` is the HTTP status (when available); ``detail`` is a *sanitized*
    short reason, never the full upstream body.
    """

    def __init__(self, message: str, *, status_code: int | None = None, detail: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail


class RateLimitedError(UpstreamAPIError):
    """Raised when an upstream API rate-limits us (HTTP 429) after retries."""


class SuiServiceError(UpstreamAPIError):
    """Raised when the external NestJS Sui service returns an error (D5)."""
