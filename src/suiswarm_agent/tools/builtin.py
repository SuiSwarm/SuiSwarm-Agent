from datetime import datetime, timezone

from langchain_core.tools import tool


@tool
def get_utc_time() -> str:
    """Return the current UTC time in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


@tool
def describe_project() -> str:
    """Describe the current AI agent project."""
    return (
        "SuiSwarm Agent is a LangGraph-based AI agent scaffold with a "
        "planner, tool executor, and responder node. Tools are registered "
        "under src/suiswarm_agent/tools."
    )

