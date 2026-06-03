from langchain_core.messages import HumanMessage, SystemMessage

from suiswarm_agent.llm import build_chat_model
from suiswarm_agent.prompts import PLANNER_SYSTEM_PROMPT, RESPONDER_SYSTEM_PROMPT
from suiswarm_agent.schemas import PlanDecision, ToolExecutionResult
from suiswarm_agent.state import AgentState
from suiswarm_agent.tools.registry import TOOL_REGISTRY, render_tool_catalog

CONVERSATION_CONTEXT_LIMIT = 100


def _latest_user_request(state: AgentState) -> str:
    for message in reversed(state.get("messages", [])):
        if isinstance(message, HumanMessage):
            return str(message.content)
    return ""


def _recent_messages(state: AgentState) -> list:
    return state.get("messages", [])[-CONVERSATION_CONTEXT_LIMIT:]


def _format_conversation(state: AgentState) -> str:
    lines = []
    for message in _recent_messages(state):
        role = getattr(message, "type", message.__class__.__name__)
        lines.append(f"{role}: {message.content}")
    return "\n".join(lines)


def plan_request(state: AgentState) -> dict:
    model = build_chat_model(temperature=0).with_structured_output(
        PlanDecision,
        method="function_calling",
    )
    tool_catalog = render_tool_catalog()
    conversation = _format_conversation(state)

    plan = model.invoke(
        [
            SystemMessage(
                content=f"{PLANNER_SYSTEM_PROMPT}\n\nAvailable tools:\n{tool_catalog}"
            ),
            HumanMessage(content=f"Conversation context:\n{conversation}"),
        ]
    )

    if plan.action == "use_tool" and plan.tool_name not in TOOL_REGISTRY:
        plan = PlanDecision(
            action="answer",
            reasoning=(
                f"Planner selected unknown tool '{plan.tool_name}', so responding "
                "without a tool."
            ),
        )

    return {
        "plan": plan,
        "selected_tool": plan.tool_name,
        "tool_input": plan.tool_input,
        "tool_error": None,
    }


def execute_tool(state: AgentState) -> dict:
    tool_name = state.get("selected_tool")
    tool_input = state.get("tool_input", {})

    if not tool_name:
        return {"tool_error": "No tool selected."}

    tool = TOOL_REGISTRY.get(tool_name)
    if tool is None:
        return {"tool_error": f"Unknown tool: {tool_name}"}

    try:
        output = tool.invoke(tool_input)
        result = ToolExecutionResult(
            tool_name=tool_name,
            input=tool_input,
            output=output,
        )
        return {"tool_result": result, "tool_error": None}
    except Exception as exc:
        result = ToolExecutionResult(
            tool_name=tool_name,
            input=tool_input,
            error=str(exc),
        )
        return {"tool_result": result, "tool_error": str(exc)}


def respond(state: AgentState) -> dict:
    model = build_chat_model(temperature=0.2)
    conversation = _format_conversation(state)
    plan = state.get("plan")
    tool_result = state.get("tool_result")

    response = model.invoke(
        [
            SystemMessage(content=RESPONDER_SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    f"Conversation context:\n{conversation}\n\n"
                    f"Planner decision:\n{plan}\n\n"
                    f"Tool result:\n{tool_result}"
                )
            ),
        ]
    )

    return {"messages": [response], "final_response": str(response.content)}
