from typing import Annotated
from uuid import uuid4

from openai import OpenAIError
import typer
from langchain_core.messages import AnyMessage, HumanMessage
from rich.console import Console

from suiswarm_agent.graph import graph
from suiswarm_agent.observability import build_langfuse_config, flush_langfuse

SESSION_MESSAGE_LIMIT = 100

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.callback()
def main() -> None:
    """SuiSwarm Agent command line interface."""


def trim_session_messages(messages: list[AnyMessage]) -> list[AnyMessage]:
    """Keep the most recent messages for the active CLI chat session."""
    return messages[-SESSION_MESSAGE_LIMIT:]


def _run_turn(
    messages: list[AnyMessage],
    message: str,
    *,
    session_id: str,
    user_id: str | None = None,
) -> list[AnyMessage]:
    try:
        session_messages = trim_session_messages(
            [*messages, HumanMessage(content=message)]
        )
        result = graph.invoke(
            {"messages": session_messages},
            config=build_langfuse_config(session_id=session_id, user_id=user_id),
        )
        final_message = result["messages"][-1]
        console.print(final_message.content)
        return trim_session_messages(result["messages"])
    except OpenAIError as exc:
        console.print(f"[red]OpenAI error:[/red] {exc}")
    except Exception as exc:
        console.print(f"[red]Agent error:[/red] {exc}")
    return messages


@app.command()
def chat(
    message: Annotated[
        str | None,
        typer.Argument(help="Optional one-shot message. Omit to start interactive chat."),
    ] = None,
    session_id: Annotated[
        str | None,
        typer.Option(
            "--session-id",
            help="Langfuse session id. Defaults to a generated CLI session id.",
        ),
    ] = None,
    user_id: Annotated[
        str | None,
        typer.Option("--user-id", help="Optional Langfuse user id."),
    ] = None,
) -> None:
    """Chat with the LangGraph agent."""
    messages: list[AnyMessage] = []
    active_session_id = session_id or f"cli-{uuid4()}"

    try:
        if message:
            _run_turn(
                messages,
                message,
                session_id=active_session_id,
                user_id=user_id,
            )
            return

        console.print("[dim]SuiSwarm Agent CLI. Type 'exit' or 'quit' to stop.[/dim]")

        while True:
            try:
                user_input = typer.prompt("You").strip()
            except (EOFError, KeyboardInterrupt):
                console.print()
                break

            if not user_input:
                continue

            if user_input.lower() in {"exit", "quit"}:
                break

            messages = _run_turn(
                messages,
                user_input,
                session_id=active_session_id,
                user_id=user_id,
            )
    finally:
        flush_langfuse()


if __name__ == "__main__":
    app()
