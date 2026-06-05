"""Factory for ReAct sub-agents.

Each sub-agent is a ``create_react_agent`` graph: it natively chains its own tool calls
(resolve id -> fetch details), which the old single-pass planner could not do.
"""

from __future__ import annotations

from collections.abc import Sequence

from langchain_core.tools import BaseTool
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent

from suiswarm_agent.llm.factory import Role, get_chat_model


def build_worker_agent(
    *,
    name: str,
    tools: Sequence[BaseTool],
    prompt: str,
    role: Role = "worker",
) -> CompiledStateGraph:
    """Build a named ReAct agent over the given tools.

    Sub-agents are compiled without a checkpointer; the supervisor graph owns
    persistence when it is compiled.
    """
    return create_react_agent(
        get_chat_model(role),
        tools=list(tools),
        prompt=prompt,
        name=str(name),
    )
