from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from suiswarm_agent.settings import get_settings
from suiswarm_agent.state import AgentState
from suiswarm_agent.tools import TOOLS

SYSTEM_PROMPT = """You are SuiSwarm Agent, a practical AI agent built with LangGraph.
Use tools when they help. Keep answers concise, concrete, and useful.
"""


def _build_model() -> ChatOpenAI:
    settings = get_settings()
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.2,
    ).bind_tools(TOOLS)


def call_model(state: AgentState) -> dict:
    model = _build_model()
    messages = [SystemMessage(content=SYSTEM_PROMPT), *state["messages"]]
    response = model.invoke(messages)
    return {"messages": [response]}


def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("agent", call_model)
    workflow.add_node("tools", ToolNode(TOOLS))

    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", tools_condition)
    workflow.add_edge("tools", "agent")

    return workflow.compile()


graph = build_graph()
