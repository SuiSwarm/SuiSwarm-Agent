"""Supervisor that routes between sub-agents (langgraph-supervisor)."""

from __future__ import annotations

from collections.abc import Sequence

from langgraph.graph.state import CompiledStateGraph, StateGraph
from langgraph_supervisor import create_supervisor

from suiswarm_agent.agent.prompts import SUPERVISOR_PROMPT
from suiswarm_agent.config.settings import Settings, get_settings
from suiswarm_agent.core.constants import AgentName
from suiswarm_agent.llm.factory import get_chat_model


def build_supervisor(
    agents: Sequence[CompiledStateGraph],
    *,
    settings: Settings | None = None,
) -> StateGraph:
    """Build the (uncompiled) supervisor graph over the given sub-agents."""
    settings = settings or get_settings()
    return create_supervisor(
        list(agents),
        model=get_chat_model("supervisor"),
        prompt=SUPERVISOR_PROMPT,
        output_mode=settings.agent.supervisor_output_mode,
        supervisor_name=str(AgentName.SUPERVISOR),
    )
