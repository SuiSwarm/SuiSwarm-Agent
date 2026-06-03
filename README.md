# SuiSwarm Agent

AI agent project scaffolded with LangGraph.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
Copy-Item .env.example .env
```

Edit `.env` and set `OPENAI_API_KEY`.
Set `TAVILY_API_KEY` to enable web search.
Set `COINGECKO_DEMO_API_KEY` to enable live crypto market lookup.

## Run the CLI

Interactive chat:

```powershell
suiswarm chat
```

The interactive CLI keeps the latest 100 messages in memory for the active session.

One-shot message:

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
  cli.py          # Command-line entry point
  graph/          # LangGraph builder and nodes
  llm.py          # Chat model factory
  prompts.py      # Planner and responder prompts
  schemas.py      # Structured planner/tool schemas
  settings.py     # Environment-based configuration
  state.py        # Shared graph state
  tools/          # Tool implementations and registry
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the planner, executor, and responder design.

## Search Tool

The agent uses Tavily through the official `langchain-tavily` integration.
Add your key in `.env`:

```env
TAVILY_API_KEY=your_tavily_api_key_here
```

## Crypto Market Tool

The agent uses CoinGecko Demo API and GeckoTerminal endpoints for live crypto market data.
Add your Demo key in `.env`:

```env
COINGECKO_DEMO_API_KEY=your_coingecko_demo_api_key_here
```

Current crypto tool coverage:

```text
Coin search and ID resolution
Live coin markets, details, top movers
Historical market charts and OHLC candles
Token lookup by contract address
Global crypto and DeFi market stats
Categories, exchanges, exchange tickers, BTC exchange rates
NFT collection details
GeckoTerminal networks, DEXes, on-chain token prices/info
Trending/new pools and pool/token search
```

## LangGraph

The graph is exposed as `graph` in `src/suiswarm_agent/graph/builder.py` and configured in `langgraph.json`.

Current graph shape:

```text
START -> plan -> execute_tool -> respond -> END
              \-> respond -> END
```

## Tests

```powershell
python -m unittest discover
```
