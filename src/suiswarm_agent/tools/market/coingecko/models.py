"""Response envelope + data-shaping helpers for CoinGecko/GeckoTerminal results.

The upstream JSON shapes are large and volatile, so we don't model every field as a
strict pydantic schema. Instead we wrap responses in a small, predictable envelope and
down-sample large series so the LLM context stays manageable.
"""

from __future__ import annotations

from typing import Any


def base_response(
    endpoint: str,
    data: Any,
    params: dict[str, Any] | None = None,
    *,
    source: str = "coingecko",
    plan: str = "demo",
    **extra: Any,
) -> dict[str, Any]:
    """Wrap raw upstream data in a consistent envelope."""
    return {
        "source": source,
        "plan": plan,
        "endpoint": endpoint,
        "params": params or {},
        "data": data,
        **extra,
    }


def sample_points(points: list[Any], max_points: int) -> list[Any]:
    """Evenly down-sample a list while preserving the final point."""
    if max_points <= 0 or len(points) <= max_points:
        return points
    step = max(1, len(points) // max_points)
    sampled = points[::step][:max_points]
    if sampled and sampled[-1] != points[-1]:
        sampled[-1] = points[-1]
    return sampled


def sample_chart(data: dict[str, Any], max_points: int) -> dict[str, Any]:
    """Down-sample each series in a CoinGecko market-chart payload."""
    return {
        key: sample_points(value, max_points) if isinstance(value, list) else value
        for key, value in data.items()
    }
