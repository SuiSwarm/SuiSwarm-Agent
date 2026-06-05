"""Swarm state.

The supervisor and ReAct sub-agents operate over LangGraph's message state. We alias it
here so future custom channels (scratchpad, active-agent metadata) have a home without
touching call sites.
"""

from __future__ import annotations

from langgraph.graph import MessagesState

# The swarm currently uses the built-in message-reducer state.
AgentState = MessagesState

__all__ = ["AgentState"]
