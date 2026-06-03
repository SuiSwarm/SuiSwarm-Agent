from typing import Any, Literal

from pydantic import BaseModel, Field


class PlanDecision(BaseModel):
    action: Literal["answer", "use_tools"] = Field(
        description="Whether to answer directly or call one or more tools first."
    )
    reasoning: str = Field(description="Short explanation of the decision.")

    tool_steps: list["ToolPlanStep"] = Field(
        default_factory=list,
        description="Ordered tool calls to execute when action is use_tools.",
    )


class ToolPlanStep(BaseModel):
    tool_name: str = Field(description="Registered tool name to call.")
    tool_input: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON input passed to the selected tool.",
    )
    reason: str = Field(description="Why this tool call is needed.")


class ToolExecutionResult(BaseModel):
    step_index: int
    tool_name: str
    reason: str | None = None
    input: dict[str, Any]
    output: Any | None = None
    error: str | None = None
