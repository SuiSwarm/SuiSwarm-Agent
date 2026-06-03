import os
from typing import Any

from dotenv import load_dotenv


LANGFUSE_TAGS = ["suiswarm-agent", "cli", "langgraph"]


def is_langfuse_configured() -> bool:
    load_dotenv()
    return all(
        os.getenv(name)
        for name in (
            "LANGFUSE_PUBLIC_KEY",
            "LANGFUSE_SECRET_KEY",
            "LANGFUSE_BASE_URL",
        )
    )


def build_langfuse_config(
    *,
    session_id: str,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Build LangChain callback config for Langfuse tracing."""
    if not is_langfuse_configured():
        return {}

    from langfuse.langchain import CallbackHandler

    metadata: dict[str, Any] = {
        "langfuse_session_id": session_id,
        "langfuse_tags": LANGFUSE_TAGS,
    }
    if user_id:
        metadata["langfuse_user_id"] = user_id

    return {
        "callbacks": [CallbackHandler()],
        "run_name": "suiswarm-agent-chat",
        "tags": LANGFUSE_TAGS,
        "metadata": metadata,
    }


def flush_langfuse() -> None:
    """Flush queued Langfuse events for short-lived CLI runs."""
    if not is_langfuse_configured():
        return

    from langfuse import get_client

    get_client().flush()
