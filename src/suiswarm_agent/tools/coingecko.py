from typing import Literal

import httpx
from langchain_core.tools import tool

from suiswarm_agent.settings import get_settings

COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"


def _auth_headers() -> dict[str, str]:
    api_key = get_settings().coingecko_demo_api_key
    if not api_key:
        raise ValueError(
            "Missing COINGECKO_DEMO_API_KEY. Add your CoinGecko Demo API key to .env."
        )
    return {"x-cg-demo-api-key": api_key}


def _get(path: str, params: dict) -> object:
    response = httpx.get(
        f"{COINGECKO_BASE_URL}{path}",
        headers=_auth_headers(),
        params=params,
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


@tool
def coingecko_search_coin_market(
    query: str,
    vs_currency: str = "usd",
    lookup: Literal["auto", "ids", "symbols", "names"] = "auto",
) -> dict:
    """Fetch live CoinGecko market data for a coin by ID, symbol, or name using the Demo API."""
    normalized_query = query.strip()
    if not normalized_query:
        raise ValueError("query is required.")

    attempts: list[tuple[str, dict[str, str]]] = []
    slug_query = normalized_query.lower().replace(" ", "-")

    if lookup in {"auto", "ids"}:
        attempts.append(("ids", {"ids": slug_query}))
    if lookup in {"auto", "symbols"}:
        attempts.append(
            (
                "symbols",
                {
                    "symbols": normalized_query.lower(),
                    "include_tokens": "top",
                },
            )
        )
    if lookup in {"auto", "names"}:
        attempts.append(("names", {"names": normalized_query}))

    last_error: str | None = None
    for matched_by, lookup_params in attempts:
        params = {
            "vs_currency": vs_currency.lower(),
            "order": "market_cap_desc",
            "per_page": "10",
            "page": "1",
            "sparkline": "false",
            "price_change_percentage": "1h,24h,7d,30d",
            **lookup_params,
        }

        try:
            data = _get("/coins/markets", params)
        except httpx.HTTPStatusError as exc:
            last_error = f"{exc.response.status_code}: {exc.response.text}"
            continue

        if isinstance(data, list) and data:
            return {
                "source": "coingecko",
                "plan": "demo",
                "endpoint": "/coins/markets",
                "matched_by": matched_by,
                "query": normalized_query,
                "vs_currency": vs_currency.lower(),
                "results": data,
            }

    return {
        "source": "coingecko",
        "plan": "demo",
        "endpoint": "/coins/markets",
        "query": normalized_query,
        "vs_currency": vs_currency.lower(),
        "results": [],
        "error": last_error,
    }

