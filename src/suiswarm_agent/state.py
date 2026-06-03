from typing import Annotated, Any

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing_extensions import NotRequired, TypedDict


class AgentState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    plan: NotRequired[Any]
    selected_tool: NotRequired[str | None]
    tool_input: NotRequired[dict[str, Any]]
    tool_result: NotRequired[Any]
    tool_error: NotRequired[str | None]
    final_response: NotRequired[str]
