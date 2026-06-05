"""Tool registry: conditional registration by configured credentials."""

from __future__ import annotations

from suiswarm_agent.config.settings import CoinGeckoSettings, SuiServiceSettings
from suiswarm_agent.tools.registry import (
    market_tools,
    research_tools,
    sui_tools,
    system_tools,
    tool_names,
)


def test_market_tools_present_when_configured(make_settings) -> None:
    settings = make_settings(coingecko=CoinGeckoSettings(demo_api_key="k"))
    tools = market_tools(settings)
    assert len(tools) == 25  # 17 CoinGecko + 8 GeckoTerminal
    names = {t.name for t in tools}
    assert "coingecko_search" in names
    assert "geckoterminal_trending_pools" in names


def test_market_tools_absent_without_key(make_settings) -> None:
    assert market_tools(make_settings(coingecko=CoinGeckoSettings())) == []


def test_sui_tools_toggle(make_settings) -> None:
    enabled = make_settings(sui_service=SuiServiceSettings(base_url="http://nest:3000"))
    assert len(sui_tools(enabled)) == 1
    assert sui_tools(make_settings(sui_service=SuiServiceSettings())) == []


def test_system_tools_always_available(make_settings) -> None:
    names = {t.name for t in system_tools(make_settings())}
    assert names == {"get_utc_time", "describe_project"}


def test_research_tools_absent_without_tavily(make_settings) -> None:
    assert research_tools(make_settings()) == []


def test_tool_names_helper(make_settings) -> None:
    settings = make_settings(coingecko=CoinGeckoSettings(demo_api_key="k"))
    assert "describe_project" in tool_names(settings)
