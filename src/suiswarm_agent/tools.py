from datetime import datetime, timezone

from langchain_core.tools import tool
from langchain_tavily import TavilySearch
from dotenv import load_dotenv


load_dotenv()


tavily_search = TavilySearch(
    max_results=5,
    topic="general",
    include_answer=True,
    search_depth="basic",
)


@tool
def get_utc_time() -> str:
    """Return the current UTC time in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


@tool
def describe_project() -> str:
    """Describe the current AI agent project."""
    return (
        "SuiSwarm Agent is a LangGraph-based AI agent scaffold. "
        "It currently supports conversational reasoning and simple tools, "
        "and is structured so more domain-specific tools can be added in "
        "src/suiswarm_agent/tools.py."
    )


TOOLS = [tavily_search, get_utc_time, describe_project]
