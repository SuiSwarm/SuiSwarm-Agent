# SuiSwarm Agent

AI agent project scaffolded with LangGraph.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
Copy-Item .env.example .env
```

Edit `.env` and set `OPENAI_API_KEY`.
Set `TAVILY_API_KEY` to enable web search.

## Run the CLI

```powershell
suiswarm chat "Explain what SuiSwarm Agent can do"
```

Or run the module directly:

```powershell
python -m suiswarm_agent.cli chat "What time is it?"
```

## Project Layout

```text
src/suiswarm_agent/
  cli.py       # Command-line entry point
  graph.py     # LangGraph graph definition
  settings.py  # Environment-based configuration
  state.py     # Shared graph state
  tools.py     # Agent tools
```

## Search Tool

The agent uses Tavily through the official `langchain-tavily` integration.
Add your key in `.env`:

```env
TAVILY_API_KEY=your_tavily_api_key_here
```

## LangGraph

The graph is exposed as `graph` in `src/suiswarm_agent/graph.py` and configured in `langgraph.json`.
