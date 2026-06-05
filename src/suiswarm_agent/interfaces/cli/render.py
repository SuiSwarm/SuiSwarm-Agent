"""Rendering helpers for the CLI (token streaming)."""

from __future__ import annotations

import sys
from typing import Any

from langchain_core.messages import AIMessageChunk
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from suiswarm_agent.core.constants import AgentName


async def stream_final_answer(
    graph: CompiledStateGraph,
    inputs: dict[str, Any],
    config: RunnableConfig,
) -> str:
    """Stream the supervisor's final-answer tokens to stdout and return the full text.

    Only supervisor-node AI text is shown; sub-agent/tool chatter stays hidden.
    """
    supervisor = str(AgentName.SUPERVISOR)
    parts: list[str] = []
    async for chunk, meta in graph.astream(inputs, config=config, stream_mode="messages"):
        if not isinstance(meta, dict) or meta.get("langgraph_node") != supervisor:
            continue
        if isinstance(chunk, AIMessageChunk) and isinstance(chunk.content, str) and chunk.content:
            sys.stdout.write(chunk.content)
            sys.stdout.flush()
            parts.append(chunk.content)
    sys.stdout.write("\n")
    sys.stdout.flush()
    return "".join(parts)
