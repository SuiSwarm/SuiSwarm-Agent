"""Market-data sub-agent (CoinGecko + GeckoTerminal)."""

from __future__ import annotations

from langgraph.graph.state import CompiledStateGraph

from suiswarm_agent.agent.agents.base import build_worker_agent
from suiswarm_agent.agent.prompts import MARKET_PROMPT
from suiswarm_agent.config.settings import Settings
from suiswarm_agent.core.constants import AgentName
from suiswarm_agent.tools.registry import market_tools, system_tools


def build_market_agent(settings: Settings | None = None) -> CompiledStateGraph:
    tools = [*market_tools(settings), *system_tools(settings)]
    return build_worker_agent(name=AgentName.MARKET, tools=tools, prompt=MARKET_PROMPT)
