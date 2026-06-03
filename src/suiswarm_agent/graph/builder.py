from langgraph.graph import END, START, StateGraph

from suiswarm_agent.graph.nodes import execute_tool, plan_request, respond
from suiswarm_agent.state import AgentState


def route_after_plan(state: AgentState) -> str:
    plan = state.get("plan")
    if plan and plan.action == "use_tool":
        return "execute_tool"
    return "respond"


def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("plan", plan_request)
    workflow.add_node("execute_tool", execute_tool)
    workflow.add_node("respond", respond)

    workflow.add_edge(START, "plan")
    workflow.add_conditional_edges(
        "plan",
        route_after_plan,
        {
            "execute_tool": "execute_tool",
            "respond": "respond",
        },
    )
    workflow.add_edge("execute_tool", "respond")
    workflow.add_edge("respond", END)

    return workflow.compile()


graph = build_graph()
