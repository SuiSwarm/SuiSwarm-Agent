"""FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from langgraph.graph.state import CompiledStateGraph

from suiswarm_agent.config.settings import Settings


def get_graph(request: Request) -> CompiledStateGraph:
    return request.app.state.graph


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


GraphDep = Annotated[CompiledStateGraph, Depends(get_graph)]
SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
