from typing import Any, Literal

from pydantic import BaseModel, Field


class PlanDecision(BaseModel):
    action: Literal["answer", "use_tool"] = Field(
        description="Whether to answer directly or call one tool first."
    )
    reasoning: str = Field(description="Short explanation of the decision.")
    tool_name: str | None = Field(
        default=None,
        description="Selected tool name when action is use_tool.",
    )
    tool_input: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON input passed to the selected tool.",
    )


class ToolExecutionResult(BaseModel):
    tool_name: str
    input: dict[str, Any]
    output: Any | None = None
    error: str | None = None

