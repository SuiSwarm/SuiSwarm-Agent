import typer
from langchain_core.messages import HumanMessage
from rich.console import Console

from suiswarm_agent.graph import graph

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.callback()
def main() -> None:
    """SuiSwarm Agent command line interface."""


@app.command()
def chat(message: str) -> None:
    """Send one message to the LangGraph agent."""
    result = graph.invoke({"messages": [HumanMessage(content=message)]})
    final_message = result["messages"][-1]
    console.print(final_message.content)


if __name__ == "__main__":
    app()
