"""LLM-facing Sui tools.

v1 ships a single generic passthrough to the NestJS Sui service. It is only registered
when the service is configured (``SUI_SERVICE__BASE_URL``). Per D6, the agent has full
read/write access; guardrails are enforced by a separate policy-contract repo, not here.
Phase 8 replaces this with typed per-operation tools from the NestJS OpenAPI contract.
"""

from __future__ import annotations

from typing import Any, Literal

from langchain_core.tools import tool

from suiswarm_agent.tools.sui.service import get_sui_service


@tool
async def sui_service_request(
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"],
    path: str,
    query: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
) -> dict:
    """Call the SuiSwarm Sui service (NestJS) which performs all Sui on-chain operations.

    Use this to read on-chain data (balances, owned objects, coins, transactions,
    staking, DeFi positions) and to submit write operations (the service holds the
    agent's key and signs transactions). ``path`` is the service REST path, e.g.
    ``/accounts/<address>/balances``; ``query`` are URL query params; ``body`` is the
    JSON payload for write methods.
    """
    return await get_sui_service().call(method, path, query, body)


SUI_TOOLS = [sui_service_request]
