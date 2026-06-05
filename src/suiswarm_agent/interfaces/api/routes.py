"""API routes: chat, streaming chat (SSE), and health."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any, cast
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessageChunk, HumanMessage
from langchain_core.runnables import RunnableConfig

from suiswarm_agent.config.settings import Settings
from suiswarm_agent.core.constants import AgentName
from suiswarm_agent.core.exceptions import SuiSwarmError
from suiswarm_agent.core.logging import bind_correlation_id, get_logger
from suiswarm_agent.infra.observability import langfuse_run_config
from suiswarm_agent.interfaces.api.deps import GraphDep, SettingsDep
from suiswarm_agent.interfaces.api.schemas import ChatRequest, ChatResponse, HealthResponse

router = APIRouter()
logger = get_logger("api")


def _run_config(session: str, user_id: str | None, settings: Settings) -> RunnableConfig:
    raw: dict[str, Any] = {
        "configurable": {"thread_id": session},
        "recursion_limit": settings.agent.recursion_limit,
    }
    raw.update(langfuse_run_config(session_id=session, user_id=user_id, settings=settings))
    return cast(RunnableConfig, raw)


@router.get("/healthz", response_model=HealthResponse)
async def healthz(settings: SettingsDep) -> HealthResponse:
    return HealthResponse(status="ok", capabilities=settings.capabilities())


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, graph: GraphDep, settings: SettingsDep) -> ChatResponse:
    session = req.session_id or f"api-{uuid4()}"
    bind_correlation_id(session)
    try:
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content=req.message)]},
            config=_run_config(session, req.user_id, settings),
        )
    except SuiSwarmError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return ChatResponse(answer=str(result["messages"][-1].content), session_id=session)


@router.post("/chat/stream")
async def chat_stream(
    req: ChatRequest, graph: GraphDep, settings: SettingsDep
) -> StreamingResponse:
    session = req.session_id or f"api-{uuid4()}"
    bind_correlation_id(session)
    supervisor = str(AgentName.SUPERVISOR)
    config = _run_config(session, req.user_id, settings)
    inputs = {"messages": [HumanMessage(content=req.message)]}

    async def event_stream() -> AsyncIterator[str]:
        try:
            async for chunk, meta in graph.astream(inputs, config=config, stream_mode="messages"):
                if not isinstance(meta, dict) or meta.get("langgraph_node") != supervisor:
                    continue
                if (
                    isinstance(chunk, AIMessageChunk)
                    and isinstance(chunk.content, str)
                    and chunk.content
                ):
                    yield f"data: {json.dumps({'token': chunk.content})}\n\n"
            yield f"data: {json.dumps({'done': True, 'session_id': session})}\n\n"
        except SuiSwarmError as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
        except Exception:
            logger.exception("Streaming error")
            yield f"data: {json.dumps({'error': 'internal error'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
