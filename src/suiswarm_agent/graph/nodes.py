from langchain_core.messages import HumanMessage, SystemMessage

from suiswarm_agent.llm import build_chat_model
from suiswarm_agent.prompts import PLANNER_SYSTEM_PROMPT, RESPONDER_SYSTEM_PROMPT
from suiswarm_agent.schemas import PlanDecision, ToolExecutionResult
from suiswarm_agent.state import AgentState
from suiswarm_agent.tools.registry import TOOL_REGISTRY, render_tool_catalog

CONVERSATION_CONTEXT_LIMIT = 100
MAX_TOOL_STEPS = 5


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
    user_request = _latest_user_request(state)

    plan = model.invoke(
        [
            SystemMessage(
                content=f"{PLANNER_SYSTEM_PROMPT}\n\nAvailable tools:\n{tool_catalog}"
            ),
            HumanMessage(
                content=(
                    f"Latest user request:\n{user_request}\n\n"
                    f"Conversation context:\n{conversation}"
                )
            ),
        ]
    )

    valid_steps = []
    invalid_tools = []
    for step in plan.tool_steps[:MAX_TOOL_STEPS]:
        if step.tool_name in TOOL_REGISTRY:
            valid_steps.append(step)
        else:
            invalid_tools.append(step.tool_name)

    if plan.action == "use_tools" and not valid_steps:
        plan = PlanDecision(
            action="answer",
            reasoning=(
                "Planner selected no valid registered tools, so responding without "
                f"tools. Invalid tools: {invalid_tools}"
            ),
        )
    elif plan.action == "use_tools":
        plan.tool_steps = valid_steps

    return {
        "plan": plan,
        "tool_results": [],
        "tool_error": None,
    }


def execute_tools(state: AgentState) -> dict:
    plan = state.get("plan")
    if not plan or plan.action != "use_tools":
        return {"tool_results": [], "tool_error": None}

    results = []
    errors = []

    for index, step in enumerate(plan.tool_steps[:MAX_TOOL_STEPS], start=1):
        tool = TOOL_REGISTRY.get(step.tool_name)
        if tool is None:
            error = f"Unknown tool: {step.tool_name}"
            errors.append(error)
            results.append(
                ToolExecutionResult(
                    step_index=index,
                    tool_name=step.tool_name,
                    reason=step.reason,
                    input=step.tool_input,
                    error=error,
                )
            )
            continue

        try:
            output = tool.invoke(step.tool_input)
            results.append(
                ToolExecutionResult(
                    step_index=index,
                    tool_name=step.tool_name,
                    reason=step.reason,
                    input=step.tool_input,
                    output=output,
                )
            )
        except Exception as exc:
            error = str(exc)
            errors.append(error)
            results.append(
                ToolExecutionResult(
                    step_index=index,
                    tool_name=step.tool_name,
                    reason=step.reason,
                    input=step.tool_input,
                    error=error,
                )
            )

    return {
        "tool_results": results,
        "tool_error": "\n".join(errors) if errors else None,
    }


def respond(state: AgentState) -> dict:
    model = build_chat_model(temperature=0.2)
    conversation = _format_conversation(state)
    plan = state.get("plan")
    tool_results = state.get("tool_results", [])

    response = model.invoke(
        [
            SystemMessage(content=RESPONDER_SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    f"Conversation context:\n{conversation}\n\n"
                    f"Planner decision:\n{plan}\n\n"
                    f"Tool results:\n{tool_results}"
                )
            ),
        ]
    )

    return {"messages": [response], "final_response": str(response.content)}
