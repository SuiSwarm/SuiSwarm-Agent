"""FastAPI application factory.

The swarm graph is built once on startup (lifespan), wired to a checkpointer whose
lifecycle spans the app. Importing this module does not require an LLM key; the key is
needed when the app starts up.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from suiswarm_agent import __version__
from suiswarm_agent.agent import build_graph
from suiswarm_agent.config.settings import get_settings
from suiswarm_agent.core.logging import configure_logging, get_logger
from suiswarm_agent.infra.observability import configure_langfuse, flush_langfuse
from suiswarm_agent.interfaces.api.routes import router
from suiswarm_agent.memory.checkpoint import checkpointer_context
from suiswarm_agent.tools.registry import close_clients

logger = get_logger("api")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging("INFO")
    configure_langfuse(settings)
    async with checkpointer_context(settings) as saver:
        app.state.settings = settings
        app.state.graph = build_graph(checkpointer=saver, settings=settings)
        logger.info("SuiSwarm API ready (persistence=%s)", settings.persistence.backend)
        yield
    await close_clients()
    flush_langfuse()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="SuiSwarm Agent API", version=__version__, lifespan=lifespan)
    origins = settings.server.cors_origins
    if origins:
        # Never pair credentials with a wildcard origin (forbidden by the CORS spec).
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials="*" not in origins,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.include_router(router)
    return app


app = create_app()
