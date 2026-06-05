# SuiSwarm Agent

**SuiSwarm Agent** là một "đàn" (swarm) AI agent lấy **Sui blockchain** làm trọng tâm, xây trên
**LangGraph**. Một **supervisor** điều phối các **sub-agent** chuyên biệt, mỗi agent là một agent
ReAct tự chain được tool của mình:

- **market_agent** — dữ liệu thị trường crypto (CoinGecko / GeckoTerminal).
- **research_agent** — tìm kiếm web (Tavily) cho tin tức/bối cảnh.
- **sui_onchain_agent** — thao tác on-chain Sui qua một **service NestJS riêng** (bật khi cấu hình).

> Mọi tương tác Sui (RPC, giữ key, ký tx) nằm ở service NestJS tách biệt; phía Python chỉ gọi
> REST API của nó. Xem [docs/REFACTORING_PLAN.md](docs/REFACTORING_PLAN.md) để biết toàn bộ kiến
> trúc và lộ trình.

## Cài đặt

```bash
uv venv && . .venv/bin/activate      # Windows: .venv\Scripts\Activate.ps1
uv pip install -e ".[dev]"           # hoặc: uv pip install -e .
cp .env.example .env                 # rồi điền OPENAI_API_KEY
```

Chỉ `OPENAI_API_KEY` là bắt buộc. Thêm `COINGECKO_DEMO_API_KEY` để bật market agent,
`TAVILY_API_KEY` để bật research agent, `LANGFUSE_*` để bật tracing. Xem `.env.example`.

Kiểm tra cấu hình:

```bash
suiswarm config
```

## Dùng CLI

```bash
suiswarm chat "Giá Bitcoin hiện tại là bao nhiêu USD?"     # one-shot (streaming)
suiswarm chat                                              # chat tương tác
suiswarm chat "..." --no-stream --session-id dev-1         # cờ tùy chọn
python -m suiswarm_agent chat "What can you do?"           # chạy qua module
```

Cờ hữu ích: `--session-id/--thread-id` (giữ ngữ cảnh hội thoại qua checkpointer),
`--model`, `--temperature`, `--stream/--no-stream`, `--log-level`.

## Dùng REST API

```bash
uvicorn suiswarm_agent.interfaces.api.app:app --port 8000
```

| Endpoint            | Mô tả                                  |
| ------------------- | -------------------------------------- |
| `POST /chat`        | Một lượt chat, trả JSON                |
| `POST /chat/stream` | Streaming token qua SSE                |
| `GET  /healthz`     | Health + danh sách capability đang bật |

```bash
curl -s localhost:8000/chat -H 'content-type: application/json' \
  -d '{"message":"Top 3 trending coins?"}'
```

## Docker

```bash
docker compose up --build      # API + persistence SQLite, đọc .env
```

## Cấu trúc dự án

```text
src/suiswarm_agent/
  config/        # Settings có type, hợp nhất (env nested + alias quy ước)
  core/          # constants, exceptions, logging
  llm/           # factory chat-model đa provider
  infra/         # http client (retry/rate-limit/cache), observability (langfuse)
  memory/        # checkpointer LangGraph (memory/sqlite/postgres)
  tools/         # client/service/tools theo domain: market/{coingecko,geckoterminal}, web, sui, system
  agent/         # swarm: supervisor + agents/ + prompts
  interfaces/    # cli/ (Typer, streaming) và api/ (FastAPI)
```

## Phát triển

```bash
make check     # ruff + mypy + pytest (đúng cổng CI)
make test
make serve     # uvicorn --reload
```

CI chạy lint + type-check + test trên Python 3.11–3.13. Xem [CONTRIBUTING.md](CONTRIBUTING.md).

## Tài liệu

- [docs/REFACTORING_PLAN.md](docs/REFACTORING_PLAN.md) — kiến trúc đích, quyết định D1–D6, lộ trình 8 phase.
- `docs/kien-truc/`, `docs/huong-dan/` — tổng quan, ADR, và hướng dẫn cấu hình / thêm tool / triển khai.
