# Changelog

Tất cả thay đổi đáng chú ý của dự án được ghi ở đây.
Định dạng theo [Keep a Changelog](https://keepachangelog.com/), phiên bản theo [SemVer](https://semver.org/).

## [0.2.0] - 2026-06-03

Tái cấu trúc lớn từ scaffold một-agent thành **swarm đa agent lấy Sui làm trọng tâm**
(xem `docs/REFACTORING_PLAN.md`). Đây là bản v0.x nên có thay đổi phá vỡ tương thích.

### Added
- Kiến trúc **swarm**: supervisor (`langgraph-supervisor`) điều phối các sub-agent ReAct
  (`market_agent`, `research_agent`, và `sui_onchain_agent` khi cấu hình).
- Tầng `infra/http`: HTTP client async dùng chung với retry/backoff, rate-limit, cache.
- Cấu hình hợp nhất, có type, lồng theo concern (`config/settings.py`).
- Factory LLM đa provider (`llm/factory.py`) qua `init_chat_model`.
- Logging có cấu trúc + correlation id; cây exception domain (`core/`).
- Persistence qua LangGraph checkpointer (memory / sqlite / postgres).
- **REST API** (FastAPI): `/chat`, `/chat/stream` (SSE), `/healthz`.
- CLI mới: streaming, cờ `--model/--temperature/--thread-id`, lệnh `config`.
- Seam Sui: `tools/sui` gọi service NestJS qua REST (D5/D6); tool hiện hóa ở Phase 8.
- Hạ tầng kỹ thuật: ruff + mypy + pytest, CI GitHub Actions, Docker + docker-compose,
  pre-commit, Makefile, LICENSE.

### Changed
- `graph/` → `agent/`; tách "god module" CoinGecko thành `tools/market/{coingecko,geckoterminal}`
  với các lớp client/service/models/tools; tool chạy **async**.
- `langgraph.json` trỏ tới factory `agent/graph.py:make_graph`.
- Pin theo stack thực tế đã cài: LangGraph 1.x, LangChain 1.x, Langfuse 4.x.

### Removed
- `requirements.txt` (thay bằng `pyproject.toml` + lock file).
- Planner một-lượt cũ (`graph/nodes.py`) — sub-agent ReAct tự chain tool thay thế.
