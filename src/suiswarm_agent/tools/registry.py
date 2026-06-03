from langchain_core.tools import BaseTool

from suiswarm_agent.tools.builtin import describe_project, get_utc_time
from suiswarm_agent.tools.coingecko import COINGECKO_TOOLS
from suiswarm_agent.tools.search import tavily_search


TOOLS: list[BaseTool] = [
    *COINGECKO_TOOLS,
    tavily_search,
    get_utc_time,
    describe_project,
]

TOOL_REGISTRY: dict[str, BaseTool] = {tool.name: tool for tool in TOOLS}


def render_tool_catalog() -> str:
    lines = []
    for tool in TOOLS:
        args_schema = tool.args_schema.model_json_schema() if tool.args_schema else {}
        lines.append(
            f"- {tool.name}: {tool.description}\n"
            f"  input_schema: {args_schema}"
        )
    return "\n".join(lines)
