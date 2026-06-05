"""Integration: the swarm graph compiles with the expected nodes (no LLM call)."""

from __future__ import annotations

from langgraph.graph.state import CompiledStateGraph

from suiswarm_agent.agent.graph import build_graph
from suiswarm_agent.config.settings import CoinGeckoSettings, SuiServiceSettings, TavilySettings


def test_build_graph_has_supervisor_and_workers(make_settings) -> None:
    settings = make_settings(
        coingecko=CoinGeckoSettings(demo_api_key="k"),
        tavily=TavilySettings(api_key="t"),
    )
    settings.agent.enabled_agents = ["market", "research"]
    graph = build_graph(settings=settings)
    assert isinstance(graph, CompiledStateGraph)
    nodes = set(graph.get_graph().nodes.keys())
    assert {"supervisor", "market_agent", "research_agent"} <= nodes


def test_agent_skipped_when_credential_missing(make_settings) -> None:
    # No CoinGecko key -> market agent must not be registered (truthful capabilities).
    settings = make_settings(tavily=TavilySettings(api_key="t"))
    settings.agent.enabled_agents = ["market", "research"]
    graph = build_graph(settings=settings)
    nodes = set(graph.get_graph().nodes.keys())
    assert "market_agent" not in nodes
    assert "research_agent" in nodes


def test_fallback_worker_when_no_capabilities(make_settings) -> None:
    # No keys at all -> still build a valid graph with one fallback worker.
    settings = make_settings()
    settings.agent.enabled_agents = ["market", "research"]
    graph = build_graph(settings=settings)
    nodes = set(graph.get_graph().nodes.keys())
    assert "supervisor" in nodes
    assert "research_agent" in nodes


def test_sui_agent_auto_enabled_when_service_configured(make_settings) -> None:
    settings = make_settings(
        coingecko=CoinGeckoSettings(demo_api_key="k"),
        sui_service=SuiServiceSettings(base_url="http://nest:3000"),
    )
    settings.agent.enabled_agents = ["market"]
    graph = build_graph(settings=settings)
    nodes = set(graph.get_graph().nodes.keys())
    assert "sui_onchain_agent" in nodes
