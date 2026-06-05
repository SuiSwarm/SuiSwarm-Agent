"""Sui domain service — maps intent to NestJS endpoints.

Generic in v1 (the NestJS contract is not built yet). Phase 8 adds typed methods such
as ``get_balances(address)`` / ``get_object(object_id)`` once the OpenAPI contract is
available.
"""

from __future__ import annotations

from typing import Any

from suiswarm_agent.tools.sui.client import SuiServiceClient, get_sui_client


class SuiService:
    def __init__(self, client: SuiServiceClient | None = None) -> None:
        self._client = client or get_sui_client()

    async def call(
        self,
        method: str,
        path: str,
        query: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        data = await self._client.request(method, path, params=query, json=body)
        return {"source": "sui-service", "method": method.upper(), "path": path, "data": data}


_service: SuiService | None = None


def get_sui_service() -> SuiService:
    global _service
    if _service is None:
        _service = SuiService()
    return _service
