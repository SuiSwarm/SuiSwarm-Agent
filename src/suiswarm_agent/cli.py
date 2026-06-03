from typing import Annotated

from openai import OpenAIError
import typer
from langchain_core.messages import AnyMessage, HumanMessage
from rich.console import Console

from suiswarm_agent.graph import graph

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.callback()
def main() -> None:
    """SuiSwarm Agent command line interface."""


def _run_turn(messages: list[AnyMessage], message: str) -> list[AnyMessage]:
    try:
        result = graph.invoke({"messages": [*messages, HumanMessage(content=message)]})
        final_message = result["messages"][-1]
        console.print(final_message.content)
        return result["messages"]
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
) -> None:
    """Chat with the LangGraph agent."""
    messages: list[AnyMessage] = []

    if message:
        _run_turn(messages, message)
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

        messages = _run_turn(messages, user_input)


if __name__ == "__main__":
    app()
