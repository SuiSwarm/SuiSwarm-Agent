"""SuiSwarm Agent — Sui-first multi-agent swarm built on LangGraph."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("suiswarm-agent")
except PackageNotFoundError:  # pragma: no cover - source checkout without install
    __version__ = "0.0.0"

__all__ = ["__version__"]
