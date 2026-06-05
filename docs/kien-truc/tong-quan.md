# Tổng quan kiến trúc

> Ngôn ngữ: **Tiếng Việt** (D4) · Đồng bộ với [REFACTORING_PLAN.md](../REFACTORING_PLAN.md).

Trang này mô tả kiến trúc đích của **SuiSwarm Agent**: nguyên tắc phân lớp, mô hình swarm đa
agent, ranh giới Sui qua service NestJS, luồng xử lý một request, và trách nhiệm của từng package
trong `src/suiswarm_agent/`.

> **Phạm vi v1:** service NestJS *chưa dựng*, nên swarm v1 chỉ bật sub-agent **Market-data** +
> **Research**. Sub-agent **Sui** được scaffold sẵn (seam `tools/sui/`) và bật ở **Phase 8**.
> Tài liệu vẫn mô tả kiến trúc đích đầy đủ để chuẩn bị đúng hướng.

---

## 1. Nguyên tắc phân lớp (ports-and-adapters)

Phụ thuộc đi **một chiều**, từ trên xuống:

```text
interfaces (CLI / API)
        │
        ▼
agent core (SWARM: supervisor + sub-agent ReAct)
        │
        ▼
tools (thin @tool adapters)
        │
        ▼
services (logic domain)
        │
        ▼
infra (HTTP client · LLM provider · observability · persistence · config)
```

Các quy tắc cốt lõi:

1. **Tool là adapter mỏng trên service.** Mỗi API ngoài có **client** (transport), **service**
   (hàm domain + model có type), và **`@tool` wrapper** (hướng LLM, mỏng). Logic nghiệp vụ
   **không bao giờ** nằm trong thân `@tool`.
2. **Mọi thứ cấu hình được nằm trong một `Settings` có type** (lồng theo từng concern). Code đọc
   config qua `get_settings()`, **không** đọc `os.environ` trực tiếp.
3. **Factory LLM trừu tượng hóa provider** (OpenAI/Anthropic/Azure/local), override theo vai
   (`supervisor` / `worker` / `default`).
4. **I/O bất đồng bộ** với HTTP client dùng chung có retry/backoff/rate-limit/cache; tool độc lập
   chạy song song trong nội bộ sub-agent.
5. **Dùng đúng idiom LangGraph**: checkpointer-backed thread cho memory/resume; mỗi sub-agent là
   agent ReAct (tự chain tool phụ thuộc).
6. **Observability & lỗi là mối quan tâm xuyên suốt**: logging có cấu trúc + cây exception domain
   + tracing Langfuse, wiring một lần.

---

## 2. Mô hình swarm (D2)

Thay mô hình *plan-tất-cả-rồi-chạy* một lượt bằng **swarm điều phối bởi supervisor**:

```text
                         ┌───────────────┐
            user  ─────► │  Supervisor   │  (định tuyến + tổng hợp)
                         └───┬───┬───┬────┘
              handoff/route  │   │   │
              ┌──────────────┘   │   └───────────────┐
              ▼                  ▼                    ▼
     ┌─────────────────┐ ┌──────────────┐  ┌──────────────────┐
     │ Sui On-chain    │ │ Market-data  │  │ Research / Web   │
     │ agent  (LÕI)    │ │ agent        │  │ agent            │
     │ ReAct + Sui     │ │ ReAct +      │  │ ReAct + Tavily   │
     │ service tools   │ │ CoinGecko/GT │  │                  │
     └─────────────────┘ └──────────────┘  └──────────────────┘
       (bật ở Phase 8)
```

- **Supervisor** (`agent/supervisor.py`): dựng bằng `langgraph_supervisor.create_supervisor`.
  Nhận yêu cầu, định tuyến tới một hoặc nhiều sub-agent, tổng hợp kết quả và sinh câu trả lời
  cuối. CLI stream token của supervisor.
- **Sub-agent là agent ReAct** (`agent/agents/*` qua `build_worker_agent` dùng
  `create_react_agent`): mỗi agent có prompt riêng + một **tập tool con** + có thể dùng model
  riêng. Vì là ReAct, **chain tool phụ thuộc xảy ra tự nhiên trong nội bộ sub-agent** (vd:
  `coingecko_search` → dùng id trả về → lấy chi tiết).
- **State** (`agent/state.py`): `AgentState = MessagesState` của LangGraph.

**Các sub-agent:**

| Sub-agent | Vai trò | Tập tool | Trạng thái |
|---|---|---|---|
| **Sui On-chain** *(lõi)* | Truy vấn **& thao tác** Sui (số dư, object, tx, staking, DeFi, ký/gửi tx) | `tools/sui/*` → REST API NestJS | bật ở **Phase 8** khi `SUI_SERVICE__BASE_URL` có |
| **Market-data** | Giá/market cap/volume, top movers, chart/OHLC, pool DEX (gồm mạng Sui qua GeckoTerminal) | `tools/market/coingecko/*` (17 tool), `tools/market/geckoterminal/*` (8 tool) | **v1** |
| **Research/Web** | Tin tức, tài liệu, bối cảnh | `tools/web/search.py` (Tavily) | **v1** |

> `build_graph(checkpointer, settings)` tự bật sub-agent Sui khi service được cấu hình; mặc định
> `enabled_agents=['market', 'research']`. `make_graph()` là factory tiện dụng.

---

## 3. Ranh giới Sui qua NestJS (D5, D6)

Sub-agent Sui **không gọi Sui RPC trực tiếp** từ Python. Tool của nó gọi **REST API của service
NestJS** (nơi giữ ví/khóa riêng của agent, ký & gửi tx, nói chuyện với Sui RPC):

```text
tools/sui  ──HTTP/REST──►  Service NestJS (repo khác)  ──Sui RPC──►  Sui blockchain
```

- **D5 — không giữ key, không RPC trực tiếp.** `SuiServiceClient` (`tools/sui/client.py`) chỉ là
  một HTTP client mỏng (dùng chung `AsyncHttpClient`), tương tự cách gọi CoinGecko. Việc giữ key
  / ký giao dịch / nói chuyện với Sui RPC thuộc về NestJS. Auth qua API key ở header, cấu hình
  bằng `SUI_SERVICE__BASE_URL` / `SUI_SERVICE__API_KEY` / `SUI_SERVICE__API_KEY_HEADER`. Tool
  `sui_service_request` chỉ được **đăng ký khi `SUI_SERVICE__BASE_URL` có**.
- **D6 — full quyền (đọc + ghi), không gate ở Python.** Agent được tự do thao tác đọc lẫn ghi;
  phần chặn/guardrail do một **repo policy contract riêng** đảm nhiệm, **KHÔNG gate ở agent
  này**. Đổi lại, phía Python phải **log/trace rõ mọi hành động** để audit được.

---

## 4. Luồng xử lý một request (ASCII)

```text
   user prompt
       │
       ▼
 ┌─────────────────────────── interfaces ───────────────────────────┐
 │  CLI (Typer + Rich, streaming token)   │   API (FastAPI: /chat,   │
 │  cờ --session-id/--thread-id/--model    │   /chat/stream SSE,      │
 │  --temperature/--stream                 │   /healthz; lifespan     │
 │                                         │   build graph)           │
 └───────────────────────────┬───────────────────────────────────────┘
                             │  (thread_id → checkpointer)
                             ▼
 ┌──────────────────── agent core (SWARM) ──────────────────────────┐
 │  Supervisor  ──route──►  sub-agent ReAct (market / research /     │
 │      ▲                    sui)                                     │
 │      │                       │  ReAct loop: gọi @tool, đọc kết    │
 │      └────── tổng hợp ◄───────┘  quả, chain tool phụ thuộc         │
 └───────────────────────────┬───────────────────────────────────────┘
                             │  (LLM từ llm/factory theo vai)
                             ▼
 ┌──────────────────────────── tools ────────────────────────────────┐
 │  @tool mỏng → gọi service tương ứng (đăng ký có điều kiện theo key)│
 └───────────────────────────┬───────────────────────────────────────┘
                             ▼
 ┌─────────────────────────── services ──────────────────────────────┐
 │  coingecko / geckoterminal / web / system / sui (→ NestJS REST)   │
 └───────────────────────────┬───────────────────────────────────────┘
                             ▼
 ┌──────────────────────────── infra ────────────────────────────────┐
 │  AsyncHttpClient (retry/backoff/ratelimit/cache, map lỗi)          │
 │  · llm/factory · observability(langfuse) · settings · checkpointer │
 └───────────────────────────┬───────────────────────────────────────┘
                             ▼
        APIs ngoài: CoinGecko · GeckoTerminal (/onchain) · Tavily
        · Service NestJS (Sui)            tracing → Langfuse (tùy chọn)
```

---

## 5. Bảng trách nhiệm từng package (src/suiswarm_agent/)

| Package / module | Trách nhiệm |
|---|---|
| `config/settings.py` | Một `Settings` có type, **lồng** theo concern: `LLMSettings`, `CoinGeckoSettings`, `TavilySettings`, `SuiServiceSettings`, `LangfuseSettings`, `HTTPSettings`, `AgentSettings`, `PersistenceSettings`, `ServerSettings`. `get_settings()` cache + `load_dotenv()`; `capabilities()` trả `dict` cho biết năng lực nào đang bật. Secret theo tên quy ước được đọc ở field top-level rồi **bridge** vào model lồng bằng `model_validator` (vì pydantic-settings không áp `validation_alias` cho field của model lồng). |
| `core/constants.py` | Hằng dùng chung: `AgentName`, `ToolGroup`, `LANGFUSE_TAGS`. |
| `core/exceptions.py` | Cây exception domain: `SuiSwarmError` → `ConfigError`, `LLMError`, `ToolError` (`ToolNotFoundError`, `ToolExecutionError`, `UpstreamAPIError`, `RateLimitedError`), `SuiServiceError`. |
| `core/logging.py` | Logging có cấu trúc: `configure_logging`, `get_logger`, `bind_correlation_id`. |
| `llm/factory.py` | `get_chat_model(role='supervisor'|'worker'|'default', model=, temperature=, **overrides)` dùng `init_chat_model` của LangChain; raise `ConfigError` nếu thiếu key. Trừu tượng hóa provider, override model/temperature theo vai. |
| `infra/http/client.py` | `AsyncHttpClient` — `httpx.AsyncClient` dùng chung, retry + backoff bằng `tenacity`, `AsyncRateLimiter`, cache TTL tùy chọn, map lỗi → `UpstreamAPIError` / `RateLimitedError`. |
| `infra/observability/langfuse.py` | `configure_langfuse`, `langfuse_run_config`, `flush_langfuse`. |
| `memory/checkpoint.py` | `build_checkpointer()` → `InMemorySaver`; `checkpointer_context()` (async context manager) chọn backend `memory` / `sqlite` / `postgres`. |
| `tools/base.py` | Helper tool: `render_tool_summary`, `include_if` (đăng ký có điều kiện). |
| `tools/registry.py` | Gom tool theo nhóm (`market_tools`, `research_tools`, `system_tools`, `sui_tools`) và expose `available_tools`, `all_tools`, `tool_names`. **Đăng ký có điều kiện** theo key cấu hình — thiếu key thì tool đơn giản vắng mặt. |
| `tools/market/coingecko/{client,service,models,tools}.py` | 17 tool (tên `coingecko_*`): client/service/models/`@tool` cho CoinGecko. |
| `tools/market/geckoterminal/{service,tools}.py` | 8 tool (tên `geckoterminal_*`), dùng chung `CoinGeckoClient` qua nhánh `/onchain`. |
| `tools/web/search.py` | `build_tavily_tool` — khởi tạo Tavily **lazy** và có điều kiện. |
| `tools/system/builtin.py` | Tool nội bộ: `get_utc_time`, `describe_project`. |
| `tools/sui/{client,service,tools}.py` | `SuiServiceClient` gọi REST API NestJS; tool `sui_service_request`; **chỉ đăng ký khi `SUI_SERVICE__BASE_URL` có**. Domain lõi (D1), gọi qua NestJS (D5). |
| `agent/state.py` | `AgentState = MessagesState`. |
| `agent/prompts.py` | `SUPERVISOR_PROMPT`, `MARKET_PROMPT`, `RESEARCH_PROMPT`, `SUI_ONCHAIN_PROMPT`. |
| `agent/agents/{base,market,research,sui_onchain}.py` | `build_worker_agent` dựng sub-agent ReAct bằng `create_react_agent` (prompt + toolset + model theo vai). |
| `agent/supervisor.py` | `build_supervisor` dùng `langgraph_supervisor.create_supervisor`. |
| `agent/graph.py` | `build_graph(checkpointer, settings)` lắp ráp swarm (tự bật Sui agent khi service cấu hình; mặc định `enabled_agents=['market','research']`); `make_graph()` là factory. |
| `interfaces/cli/{app,render}.py` | CLI Typer. Lệnh `chat`, `config`; streaming token của supervisor; cờ `--session-id/--thread-id/--user-id/--model/--temperature/--stream/--no-stream/--log-level`. `render.py` chứa helper render Rich. |
| `interfaces/api/{app,routes,schemas,deps}.py` | FastAPI. `POST /chat`, `POST /chat/stream` (SSE), `GET /healthz`. Chạy bằng `uvicorn suiswarm_agent.interfaces.api.app:app`; `lifespan` build graph với checkpointer. `schemas.py` là DTO request/response; `deps.py` lo dependency injection. |

---

## 6. Tham chiếu chéo

- Các quyết định D1–D6 và lộ trình theo phase: [REFACTORING_PLAN.md](../REFACTORING_PLAN.md).
- Architecture Decision Records: [kien-truc/adr/](adr/).
- Cấu hình env/Settings chi tiết: [huong-dan/cau-hinh.md](../huong-dan/cau-hinh.md).
- Thêm tool / sub-agent / LLM provider: thư mục [huong-dan/](../huong-dan/).
