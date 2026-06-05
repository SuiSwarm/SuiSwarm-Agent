"""Assemble and compile the SuiSwarm swarm graph.

``build_graph`` constructs the enabled sub-agents, wires them under the supervisor, and
compiles with a checkpointer. ``make_graph`` is the zero-arg factory referenced by
``langgraph.json`` (uses in-memory persistence).

A sub-agent is only built when its capability credential is configured, so the supervisor
never advertises a capability it cannot fulfil. At least one worker is always kept so the
supervisor graph is valid. Construction requires an LLM API key; importing this module
does not (the key is only needed when a graph is actually built).
"""

from __future__ import annotations

from collections.abc import Callable

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph

from suiswarm_agent.agent.agents import (
    build_market_agent,
    build_research_agent,
    build_sui_onchain_agent,
)
from suiswarm_agent.agent.supervisor import build_supervisor
from suiswarm_agent.config.settings import Settings, get_settings
from suiswarm_agent.core.logging import get_logger
from suiswarm_agent.memory.checkpoint import build_checkpointer
from suiswarm_agent.tools.base import render_tool_summary
from suiswarm_agent.tools.registry import all_tools

logger = get_logger(__name__)

_BUILDERS: dict[str, Callable[[Settings | None], CompiledStateGraph]] = {
    "market": build_market_agent,
    "research": build_research_agent,
    "sui": build_sui_onchain_agent,
}

# A sub-agent is only registered when its capability credential is present.
_CAPABILITY_GATE: dict[str, Callable[[Settings], bool]] = {
    "market": lambda s: s.coingecko.enabled,
    "research": lambda s: s.tavily.enabled,
    "sui": lambda s: s.sui_service.enabled,
}


def _enabled_agents(settings: Settings) -> list[CompiledStateGraph]:
    requested = list(settings.agent.enabled_agents)
    # Auto-enable the Sui agent when the NestJS service is configured (D5).
    if settings.sui_service.enabled and "sui" not in requested:
        requested.append("sui")

    agents: list[CompiledStateGraph] = []
    for key in requested:
        builder = _BUILDERS.get(key)
        if builder is None:
            logger.warning("Unknown agent '%s' in enabled_agents; skipping.", key)
            continue
        gate = _CAPABILITY_GATE.get(key)
        if gate is not None and not gate(settings):
            logger.info("Skipping '%s' agent: required credential not configured.", key)
            continue
        agents.append(builder(settings))

    if not agents:
        # Keep at least one worker so the supervisor graph is valid even with no keys.
        logger.warning(
            "No capability-backed sub-agents; falling back to a research agent (system tools only)."
        )
        agents = [build_research_agent(settings)]

    logger.info("Swarm agents enabled: %s", [a.name for a in agents])
    logger.debug("Available tools:\n%s", render_tool_summary(all_tools(settings)))
    return agents


def build_graph(
    *,
    checkpointer: BaseCheckpointSaver | None = None,
    settings: Settings | None = None,
) -> CompiledStateGraph:
    """Build and compile the supervisor swarm graph."""
    settings = settings or get_settings()
    agents = _enabled_agents(settings)
    supervisor = build_supervisor(agents, settings=settings)
    return supervisor.compile(
        checkpointer=checkpointer or build_checkpointer(settings),
        name="suiswarm",
    )


def make_graph() -> CompiledStateGraph:
    """Zero-arg factory for langgraph.json / the LangGraph dev server."""
    return build_graph()
