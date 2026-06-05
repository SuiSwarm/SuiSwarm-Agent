"""Tool-layer helpers: compact catalog rendering and conditional inclusion."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from langchain_core.tools import BaseTool


def first_line(text: str | None) -> str:
    if not text:
        return ""
    return text.strip().splitlines()[0].strip()


def render_tool_summary(tools: Sequence[BaseTool]) -> str:
    """One compact line per tool (name + first description line).

    Used in prompts instead of dumping full JSON schemas, which is token-heavy.
    """
    return "\n".join(f"- {tool.name}: {first_line(tool.description)}" for tool in tools)


def include_if(condition: bool, factory: Callable[[], Sequence[BaseTool]]) -> list[BaseTool]:
    """Return ``factory()`` only when ``condition`` is true, else an empty list.

    Enables conditional registration: a tool group is simply absent when its
    upstream credential is not configured.
    """
    return list(factory()) if condition else []
