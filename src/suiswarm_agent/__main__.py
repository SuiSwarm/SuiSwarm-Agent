"""Enable ``python -m suiswarm_agent`` to launch the CLI."""

from suiswarm_agent.interfaces.cli.app import app

if __name__ == "__main__":
    app()
