"""Sui on-chain tools — a thin client to the external NestJS Sui service (D5/D6).

This package is a *seam*: in v1 it ships a generic REST passthrough tool, active only
when ``SUI_SERVICE__BASE_URL`` is configured. Phase 8 replaces the generic tool with
typed per-operation tools generated from the NestJS OpenAPI contract.
"""

from suiswarm_agent.tools.sui.tools import SUI_TOOLS

__all__ = ["SUI_TOOLS"]
