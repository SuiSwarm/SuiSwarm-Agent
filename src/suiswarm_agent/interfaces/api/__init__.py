"""FastAPI service exposing the SuiSwarm swarm.

Note: ``app`` is intentionally not re-exported here so that
``suiswarm_agent.interfaces.api.app`` unambiguously refers to the submodule (used by
``uvicorn suiswarm_agent.interfaces.api.app:app``).
"""

from suiswarm_agent.interfaces.api.app import create_app

__all__ = ["create_app"]
