"""SuiSwarm Agent command-line interface (Typer)."""

from __future__ import annotations

import asyncio
import contextlib
import sys
from typing import Annotated, Any, cast
from uuid import uuid4

import typer
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from rich.console import Console
from rich.table import Table

from suiswarm_agent.agent import build_graph
from suiswarm_agent.config.settings import Settings, get_settings
from suiswarm_agent.core.exceptions import SuiSwarmError
from suiswarm_agent.core.logging import bind_correlation_id, configure_logging, get_logger
from suiswarm_agent.infra.observability import (
    configure_langfuse,
    flush_langfuse,
    langfuse_run_config,
)
from suiswarm_agent.interfaces.cli.render import stream_final_answer
from suiswarm_agent.memory.checkpoint import checkpointer_context

app = typer.Typer(no_args_is_help=True, add_completion=False)
console = Console()
logger = get_logger("cli")


def _force_utf8_stdout() -> None:
    """Ensure stdout/stderr can emit Unicode (e.g. Vietnamese) on Windows consoles."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            with contextlib.suppress(ValueError, OSError):  # already configured / not a tty
                reconfigure(encoding="utf-8", errors="replace")


@app.callback()
def main() -> None:
    """SuiSwarm Agent — a Sui-first multi-agent swarm."""


def _apply_overrides(settings: Settings, model: str | None, temperature: float | None) -> None:
    if model:
        settings.llm.model = model
    if temperature is not None:
        settings.llm.temperature_worker = temperature
        settings.llm.temperature_default = temperature


async def _run_turn(
    graph: CompiledStateGraph,
    message: str,
    *,
    session_id: str,
    user_id: str | None,
    stream: bool,
    settings: Settings,
) -> None:
    bind_correlation_id(session_id)
    raw: dict[str, Any] = {
        "configurable": {"thread_id": session_id},
        "recursion_limit": settings.agent.recursion_limit,
    }
    raw.update(langfuse_run_config(session_id=session_id, user_id=user_id, settings=settings))
    config = cast(RunnableConfig, raw)
    inputs: dict[str, Any] = {"messages": [HumanMessage(content=message)]}
    try:
        if stream:
            answer = await stream_final_answer(graph, inputs, config)
            if not answer.strip():
                # Fallback: supervisor streamed no text — read the persisted final state
                # (re-invoking would duplicate the user turn in the checkpointer).
                snapshot = await graph.aget_state(config)
                messages = snapshot.values.get("messages", []) if snapshot else []
                if messages:
                    console.print(messages[-1].content)
        else:
            result = await graph.ainvoke(inputs, config=config)
            console.print(result["messages"][-1].content)
    except SuiSwarmError as exc:
        console.print(f"[red]Lỗi:[/red] {exc}")
    except Exception:
        logger.exception("Unhandled error during chat turn")
        console.print("[red]Đã xảy ra lỗi không mong đợi.[/red] Xem log để biết chi tiết.")


async def _chat_async(
    *,
    message: str | None,
    session_id: str,
    user_id: str | None,
    stream: bool,
) -> None:
    settings = get_settings()
    configure_langfuse(settings)
    async with checkpointer_context(settings) as saver:
        graph = build_graph(checkpointer=saver, settings=settings)
        if message is not None:
            await _run_turn(
                graph,
                message,
                session_id=session_id,
                user_id=user_id,
                stream=stream,
                settings=settings,
            )
            return

        console.print(
            f"[dim]SuiSwarm Agent. Type 'exit' or 'quit' to stop. (session: {session_id})[/dim]"
        )
        while True:
            try:
                user_input = console.input("[bold cyan]You[/bold cyan]: ").strip()
            except (EOFError, KeyboardInterrupt):
                console.print()
                break
            if not user_input:
                continue
            if user_input.lower() in {"exit", "quit"}:
                break
            await _run_turn(
                graph,
                user_input,
                session_id=session_id,
                user_id=user_id,
                stream=stream,
                settings=settings,
            )


@app.command()
def chat(
    message: Annotated[
        str | None,
        typer.Argument(help="One-shot message. Omit to start an interactive chat."),
    ] = None,
    session_id: Annotated[
        str | None,
        typer.Option("--session-id", help="Conversation/thread id (defaults to generated)."),
    ] = None,
    thread_id: Annotated[
        str | None,
        typer.Option("--thread-id", help="Alias for --session-id (LangGraph thread id)."),
    ] = None,
    user_id: Annotated[str | None, typer.Option("--user-id", help="Optional user id.")] = None,
    model: Annotated[str | None, typer.Option("--model", help="Override the LLM model.")] = None,
    temperature: Annotated[
        float | None, typer.Option("--temperature", help="Override worker temperature.")
    ] = None,
    stream: Annotated[bool, typer.Option("--stream/--no-stream", help="Stream tokens.")] = True,
    log_level: Annotated[str, typer.Option("--log-level", help="Logging level.")] = "WARNING",
) -> None:
    """Chat with the SuiSwarm swarm."""
    _force_utf8_stdout()
    configure_logging(log_level)
    settings = get_settings()
    _apply_overrides(settings, model, temperature)
    active = thread_id or session_id or f"cli-{uuid4()}"
    try:
        asyncio.run(_chat_async(message=message, session_id=active, user_id=user_id, stream=stream))
    finally:
        flush_langfuse()


@app.command("config")
def config_check() -> None:
    """Show which capabilities are enabled based on the current configuration."""
    _force_utf8_stdout()
    configure_logging("WARNING")
    settings = get_settings()
    table = Table(title="SuiSwarm configuration")
    table.add_column("Capability")
    table.add_column("Status")
    labels = {
        "llm": f"LLM ({settings.llm.provider}:{settings.llm.model})",
        "coingecko": "CoinGecko market data",
        "tavily": "Tavily web search",
        "sui_service": "Sui service (NestJS)",
        "langfuse": "Langfuse tracing",
    }
    for key, enabled in settings.capabilities().items():
        status = "[green]enabled[/green]" if enabled else "[yellow]disabled[/yellow]"
        table.add_row(labels.get(key, key), status)
    console.print(table)


if __name__ == "__main__":
    app()
