# Architecture

SuiSwarm Agent currently uses a simple, explicit LangGraph workflow:

```text
START
  -> plan
  -> execute_tool
  -> respond
  -> END
```

If the planner decides no tool is needed, the graph skips execution:

```text
START -> plan -> respond -> END
```

## Nodes

`plan`

Receives the latest user request and chooses one of two actions:

- `answer`: respond directly without a tool.
- `use_tool`: select exactly one registered tool and provide JSON input.

`execute_tool`

Looks up the selected tool from the registry and invokes it with the planner's input.
Tool output or error is written back to graph state.

`respond`

Produces the final answer from the user request, planner decision, and optional tool result.
This node does not call tools.

## Extension Points

Add new tools under:

```text
src/suiswarm_agent/tools/
```

Then register them in:

```text
src/suiswarm_agent/tools/registry.py
```

Add or evolve graph state in:

```text
src/suiswarm_agent/state.py
```

Add structured outputs in:

```text
src/suiswarm_agent/schemas.py
```

This keeps planning, execution, response generation, tool implementation, and data contracts separate.

Currently registered tool groups include:

- CoinGecko aggregated market tools: search, live markets, details, top movers,
  charts, OHLC, contracts, global data, categories, exchanges, NFT details.
- GeckoTerminal on-chain tools: networks, DEXes, token prices/info, token pools,
  trending/new pools, pool search.
- `tavily_search`: web search.
- `get_utc_time`: UTC clock.
- `describe_project`: project description.
