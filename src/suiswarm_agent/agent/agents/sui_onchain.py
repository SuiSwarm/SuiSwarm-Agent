"""Sui on-chain sub-agent (calls the external NestJS Sui service).

Activated only when the Sui service is configured (``SUI_SERVICE__BASE_URL``). In v1 the
NestJS service is not built, so this agent is normally inactive.
"""

from __future__ import annotations

from langgraph.graph.state import CompiledStateGraph

from suiswarm_agent.agent.agents.base import build_worker_agent
from suiswarm_agent.agent.prompts import SUI_ONCHAIN_PROMPT
from suiswarm_agent.config.settings import Settings
from suiswarm_agent.core.constants import AgentName
from suiswarm_agent.tools.registry import sui_tools, system_tools


def build_sui_onchain_agent(settings: Settings | None = None) -> CompiledStateGraph:
    tools = [*sui_tools(settings), *system_tools(settings)]
    return build_worker_agent(name=AgentName.SUI_ONCHAIN, tools=tools, prompt=SUI_ONCHAIN_PROMPT)
