"""Request/response DTOs for the API."""

from __future__ import annotations

from pydantic import BaseModel, Field

_ID_PATTERN = r"^[A-Za-z0-9._:-]{1,128}$"


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000, description="User message.")
    session_id: str | None = Field(
        default=None,
        pattern=_ID_PATTERN,
        description="Conversation/thread id; generated when omitted.",
    )
    user_id: str | None = Field(
        default=None, pattern=_ID_PATTERN, description="Optional user id for tracing."
    )


class ChatResponse(BaseModel):
    answer: str
    session_id: str


class HealthResponse(BaseModel):
    status: str
    capabilities: dict[str, bool]
