# SuiSwarm Agent — Hướng dẫn cấu hình

> Ngôn ngữ: Tiếng Việt (thuật ngữ kỹ thuật giữ tiếng Anh khi đó là chuẩn ngành) ·
> Nhất quán với [`docs/REFACTORING_PLAN.md`](../REFACTORING_PLAN.md).
>
> Tài liệu này là **tham chiếu đầy đủ** về cấu hình của SuiSwarm Agent — một swarm đa agent
> lấy Sui blockchain làm trọng tâm, xây trên LangGraph (supervisor + sub-agent ReAct).

---

## Mục lục

1. [Hai kiểu biến môi trường](#1-hai-kiểu-biến-môi-trường)
2. [Cách `get_settings()` và `capabilities()` hoạt động](#2-cách-get_settings-và-capabilities-hoạt-động)
3. [Bảng tham chiếu đầy đủ biến môi trường](#3-bảng-tham-chiếu-đầy-đủ-biến-môi-trường)
4. [Lệnh `suiswarm config`](#4-lệnh-suiswarm-config)
5. [Ví dụ `.env` tối thiểu](#5-ví-dụ-env-tối-thiểu)
6. [Ví dụ `.env` đầy đủ](#6-ví-dụ-env-đầy-đủ)

---

## 1. Hai kiểu biến môi trường

Cấu hình SuiSwarm Agent được nạp qua **một `Settings` có type duy nhất**
(`src/suiswarm_agent/config/settings.py`, dựa trên `pydantic-settings`). Có **hai kiểu** đặt tên
biến môi trường, phục vụ hai mục đích khác nhau:

### Kiểu A — Tên quy ước (cho secret)

Dùng cho các **bí mật/khóa API** theo tên quy ước phổ biến của từng nhà cung cấp, để bạn dán
nguyên xi key từ dashboard mà không phải nhớ cú pháp lồng:

| Tên quy ước | Bridge vào |
|---|---|
| `OPENAI_API_KEY` | `llm.api_key` |
| `COINGECKO_DEMO_API_KEY` (hoặc `COINGECKO_API_KEY`) | `coingecko.demo_api_key` |
| `TAVILY_API_KEY` | `tavily.api_key` |
| `LANGFUSE_PUBLIC_KEY` | `langfuse.public_key` |
| `LANGFUSE_SECRET_KEY` | `langfuse.secret_key` |
| `LANGFUSE_BASE_URL` (hoặc `LANGFUSE_HOST`) | `langfuse.host` |

### Kiểu B — Tên lồng với dấu `__` (cho cấu hình có cấu trúc)

Dùng cho **mọi cấu hình có cấu trúc** còn lại. Cú pháp là `SECTION__FIELD`, với `__` (hai gạch
dưới) là `env_nested_delimiter`. Ví dụ `LLM__MODEL` map vào `settings.llm.model`,
`HTTP__TIMEOUT` map vào `settings.http.timeout`, `SUI_SERVICE__BASE_URL` map vào
`settings.sui_service.base_url`.

Các section (model lồng) gồm: `LLM`, `COINGECKO`, `TAVILY`, `SUI_SERVICE`, `LANGFUSE`, `HTTP`,
`AGENT`, `PERSISTENCE`, `SERVER`.

### Vì sao phải có cơ chế "bridge"

`pydantic-settings` **không** áp `validation_alias` cho field nằm trong model lồng. Do đó secret
theo tên quy ước (Kiểu A) được khai báo ở **field top-level** của `Settings` (với
`validation_alias`), rồi được **bridge** vào model lồng tương ứng bằng một
`model_validator(mode="after")` (`_bridge_conventional_secrets`).

Hệ quả thực dụng:

- Bạn có thể dùng `OPENAI_API_KEY` (Kiểu A) **hoặc** `LLM__API_KEY` (Kiểu B) cho cùng một khóa.
- Khi cả hai cùng tồn tại, giá trị đặt **trực tiếp ở field lồng** (Kiểu B) được ưu tiên; tên quy
  ước chỉ điền vào khi field lồng còn trống (`self.llm.api_key = self.llm.api_key or ...`).
- Riêng `LANGFUSE_BASE_URL`/`LANGFUSE_HOST` chỉ ghi đè `langfuse.host` khi có giá trị.

> Lưu ý: `case_sensitive=False` và `extra="ignore"` — tên biến không phân biệt hoa/thường, và các
> biến lạ trong môi trường bị bỏ qua thay vì gây lỗi.

---

## 2. Cách `get_settings()` và `capabilities()` hoạt động

### `get_settings()`

```python
from suiswarm_agent.config.settings import get_settings

settings = get_settings()
```

- Được bọc `@lru_cache(maxsize=1)` → trả về **một singleton** dùng chung cho cả tiến trình; chỉ
  khởi tạo `Settings()` đúng một lần.
- Lần gọi đầu sẽ chạy `load_dotenv()` để nạp file `.env` ở thư mục làm việc vào môi trường.
- Đây là **nguồn duy nhất** đọc cấu hình: không module nào khác đọc `os.environ` trực tiếp — tất
  cả đều đi qua `get_settings()`.

Thứ tự ưu tiên giá trị (theo `pydantic-settings`): biến môi trường thật của tiến trình → file
`.env` → giá trị mặc định khai báo trong các model.

### `capabilities()`

`settings.capabilities()` trả về `dict[str, bool]` cho biết **năng lực nào đang được bật** dựa
trên cấu hình hiện tại. Một năng lực được coi là bật khi có đủ khóa/cấu hình cần thiết:

| Khóa trong dict | Bật khi |
|---|---|
| `llm` | `llm.api_key` đã có (bắt buộc để chạy) |
| `coingecko` | `coingecko.demo_api_key` đã có |
| `tavily` | `tavily.api_key` đã có |
| `sui_service` | `sui_service.base_url` đã có |
| `langfuse` | có **cả** `public_key` lẫn `secret_key` |

`capabilities()` được dùng làm cơ sở cho lệnh `suiswarm config` (xem §4) và liên quan trực tiếp
tới việc **đăng ký tool có điều kiện** trong registry: tool `coingecko_*`/`geckoterminal_*`,
`tavily`, và `sui_service_request` chỉ được nạp khi key/`base_url` tương ứng có mặt.

---

## 3. Bảng tham chiếu đầy đủ biến môi trường

> Cột "Mặc định" lấy theo khai báo trong `config/settings.py`. Biến **bắt buộc** được đánh dấu rõ.

### 3.1. LLM — `LLMSettings`

| Biến env | Ý nghĩa | Mặc định |
|---|---|---|
| `OPENAI_API_KEY` | **(Bắt buộc)** Khóa LLM, bridge vào `llm.api_key`. | _(không có)_ |
| `LLM__API_KEY` | Khóa LLM dạng lồng (tương đương `OPENAI_API_KEY`). | _(không có)_ |
| `LLM__PROVIDER` | Provider của chat model (provider-agnostic qua `init_chat_model`). | `openai` |
| `LLM__MODEL` | Tên model. Chấp nhận dạng `provider/model` và tự bỏ prefix nếu trùng provider. | `gpt-4o-mini` |
| `LLM__BASE_URL` | Base URL cho endpoint Azure / OpenAI-compatible / local. | _(không có)_ |
| `LLM__TEMPERATURE_SUPERVISOR` | Temperature cho supervisor (định tuyến nên tất định). | `0.0` |
| `LLM__TEMPERATURE_WORKER` | Temperature cho sub-agent (worker). | `0.2` |
| `LLM__TEMPERATURE_DEFAULT` | Temperature mặc định khi không nêu role. | `0.3` |
| `LLM__REQUEST_TIMEOUT` | Timeout (giây) cho mỗi request LLM. | `60.0` |
| `LLM__MAX_RETRIES` | Số lần retry tối đa cho LLM. | `2` |

### 3.2. Market data — `CoinGeckoSettings`

| Biến env | Ý nghĩa | Mặc định |
|---|---|---|
| `COINGECKO_DEMO_API_KEY` | Khóa CoinGecko Demo (bật market sub-agent). Bí danh: `COINGECKO_API_KEY`. | _(không có)_ |
| `COINGECKO__BASE_URL` | Base URL CoinGecko (cũng phục vụ GeckoTerminal qua `/onchain`). | `https://api.coingecko.com/api/v3` |

### 3.3. Web research — `TavilySettings`

| Biến env | Ý nghĩa | Mặc định |
|---|---|---|
| `TAVILY_API_KEY` | Khóa Tavily (bật research sub-agent). | _(không có)_ |
| `TAVILY__MAX_RESULTS` | Số kết quả tối đa mỗi lần tìm. | `5` |
| `TAVILY__SEARCH_DEPTH` | Độ sâu tìm kiếm: `basic` \| `advanced`. | `basic` |
| `TAVILY__TOPIC` | Chủ đề: `general` \| `news`. | `general` |
| `TAVILY__INCLUDE_ANSWER` | Có kèm câu trả lời tóm tắt hay không. | `true` |

### 3.4. Sui service (NestJS) — `SuiServiceSettings`

> Theo D5: mọi tương tác Sui nằm ở service NestJS riêng; Python gọi qua REST, **không** RPC trực
> tiếp, **không** giữ key. Chỉ khai báo `SUI_SERVICE__BASE_URL` mới bật Sui sub-agent (Phase 8).

| Biến env | Ý nghĩa | Mặc định |
|---|---|---|
| `SUI_SERVICE__BASE_URL` | Base URL của service NestJS (bật Sui sub-agent khi có). | _(không có)_ |
| `SUI_SERVICE__API_KEY` | Khóa API gọi service NestJS. | _(không có)_ |
| `SUI_SERVICE__API_KEY_HEADER` | Tên header mang khóa API. | `x-api-key` |
| `SUI_SERVICE__TIMEOUT` | Timeout (giây) cho request tới service. | `30.0` |

### 3.5. Observability — `LangfuseSettings`

| Biến env | Ý nghĩa | Mặc định |
|---|---|---|
| `LANGFUSE_PUBLIC_KEY` | Public key Langfuse (bật tracing khi đủ cả 2 key). | _(không có)_ |
| `LANGFUSE_SECRET_KEY` | Secret key Langfuse. | _(không có)_ |
| `LANGFUSE_BASE_URL` | Host Langfuse. Bí danh: `LANGFUSE_HOST`. | `https://cloud.langfuse.com` |

### 3.6. HTTP client dùng chung — `HTTPSettings`

| Biến env | Ý nghĩa | Mặc định |
|---|---|---|
| `HTTP__TIMEOUT` | Timeout (giây) mỗi request HTTP. | `20.0` |
| `HTTP__MAX_RETRIES` | Số lần retry tối đa (tenacity). | `3` |
| `HTTP__BACKOFF_BASE` | Backoff cơ sở (giây). | `0.5` |
| `HTTP__BACKOFF_MAX` | Backoff tối đa (giây). | `8.0` |
| `HTTP__RATE_LIMIT_PER_MINUTE` | Giới hạn request/phút (tier demo CoinGecko khá chặt). | `30` |
| `HTTP__CACHE_TTL_SECONDS` | TTL cache (giây); `0` tắt cache. | `0.0` |
| `HTTP__MAX_CONNECTIONS` | Số kết nối tối đa của connection pool. | `20` |

### 3.7. Agent / swarm — `AgentSettings`

| Biến env | Ý nghĩa | Mặc định |
|---|---|---|
| `AGENT__MAX_CONVERSATION_MESSAGES` | Số message giữ trong hội thoại. | `100` |
| `AGENT__RECURSION_LIMIT` | Giới hạn đệ quy của graph LangGraph. | `40` |
| `AGENT__SUPERVISOR_OUTPUT_MODE` | Chế độ output supervisor: `full_history` \| `last_message`. | `last_message` |
| `AGENT__ENABLED_AGENTS` | Danh sách sub-agent bật. `sui` tự thêm khi Sui service được cấu hình. | `["market","research"]` |

### 3.8. Persistence (checkpointer) — `PersistenceSettings`

| Biến env | Ý nghĩa | Mặc định |
|---|---|---|
| `PERSISTENCE__BACKEND` | Backend checkpointer: `memory` \| `sqlite` \| `postgres`. | `memory` |
| `PERSISTENCE__SQLITE_PATH` | Đường dẫn file SQLite (khi backend `sqlite`). | `./.suiswarm/checkpoints.sqlite` |
| `PERSISTENCE__POSTGRES_DSN` | DSN Postgres (khi backend `postgres`). | _(không có)_ |

### 3.9. Server (FastAPI / uvicorn) — `ServerSettings`

| Biến env | Ý nghĩa | Mặc định |
|---|---|---|
| `SERVER__HOST` | Host bind của API. | `0.0.0.0` |
| `SERVER__PORT` | Cổng API. | `8000` |
| `SERVER__CORS_ORIGINS` | Danh sách origin cho CORS. | `["*"]` |

---

## 4. Lệnh `suiswarm config`

Lệnh này hiển thị **năng lực nào đang bật** theo cấu hình hiện tại — chính là kết quả của
`settings.capabilities()` (xem §2), trình bày dạng bảng (Rich):

```bash
suiswarm config
```

Bảng kết quả có 2 cột — `Capability` và `Status` (`enabled`/`disabled`) — gồm các dòng:

- `LLM (<provider>:<model>)` — ví dụ `LLM (openai:gpt-4o-mini)`.
- `CoinGecko market data`
- `Tavily web search`
- `Sui service (NestJS)`
- `Langfuse tracing`

Dùng lệnh này để kiểm tra nhanh xem `.env` đã được nạp đúng và sub-agent/tool nào sẽ được đăng
ký. (Lệnh còn lại của CLI là `suiswarm chat` để trò chuyện với swarm.)

---

## 5. Ví dụ `.env` tối thiểu

Chỉ **một** biến thực sự bắt buộc: `OPENAI_API_KEY`. Với cấu hình này, swarm chạy được nhưng
market sub-agent và research sub-agent sẽ **disabled** (không có CoinGecko/Tavily key), Sui và
Langfuse cũng tắt.

```dotenv
# Bắt buộc: khóa LLM
OPENAI_API_KEY=sk-...
```

Để có swarm v1 đúng nghĩa (market + research — mặc định `enabled_agents`), bổ sung hai khóa:

```dotenv
OPENAI_API_KEY=sk-...
COINGECKO_DEMO_API_KEY=CG-...
TAVILY_API_KEY=tvly-...
```

---

## 6. Ví dụ `.env` đầy đủ

Minh họa cả hai kiểu đặt tên (Kiểu A cho secret, Kiểu B `__` cho cấu hình có cấu trúc). Mọi dòng
không bắt buộc đều có thể bỏ đi để dùng mặc định.

```dotenv
# ---------------------------------------------------------------------------
# LLM (BẮT BUỘC)
# ---------------------------------------------------------------------------
OPENAI_API_KEY=sk-...
LLM__PROVIDER=openai
LLM__MODEL=gpt-4o-mini
# LLM__BASE_URL=https://your-azure-or-local-endpoint/v1
LLM__TEMPERATURE_SUPERVISOR=0.0
LLM__TEMPERATURE_WORKER=0.2
LLM__TEMPERATURE_DEFAULT=0.3
LLM__REQUEST_TIMEOUT=60
LLM__MAX_RETRIES=2

# ---------------------------------------------------------------------------
# Market data (bật market sub-agent)
# ---------------------------------------------------------------------------
COINGECKO_DEMO_API_KEY=CG-...
# COINGECKO__BASE_URL=https://api.coingecko.com/api/v3

# ---------------------------------------------------------------------------
# Web research (bật research sub-agent)
# ---------------------------------------------------------------------------
TAVILY_API_KEY=tvly-...
TAVILY__MAX_RESULTS=5
TAVILY__SEARCH_DEPTH=basic
TAVILY__TOPIC=general
TAVILY__INCLUDE_ANSWER=true

# ---------------------------------------------------------------------------
# Sui service (NestJS) — bật Sui sub-agent (Phase 8; v1 chưa dựng NestJS)
# ---------------------------------------------------------------------------
# SUI_SERVICE__BASE_URL=http://localhost:3000
# SUI_SERVICE__API_KEY=...
# SUI_SERVICE__API_KEY_HEADER=x-api-key
# SUI_SERVICE__TIMEOUT=30

# ---------------------------------------------------------------------------
# Observability (Langfuse — cần đủ cả public + secret key để bật)
# ---------------------------------------------------------------------------
# LANGFUSE_PUBLIC_KEY=pk-lf-...
# LANGFUSE_SECRET_KEY=sk-lf-...
# LANGFUSE_BASE_URL=https://cloud.langfuse.com

# ---------------------------------------------------------------------------
# HTTP client dùng chung (retry / rate-limit / cache)
# ---------------------------------------------------------------------------
# HTTP__TIMEOUT=20
# HTTP__MAX_RETRIES=3
# HTTP__BACKOFF_BASE=0.5
# HTTP__BACKOFF_MAX=8
# HTTP__RATE_LIMIT_PER_MINUTE=30
# HTTP__CACHE_TTL_SECONDS=0
# HTTP__MAX_CONNECTIONS=20

# ---------------------------------------------------------------------------
# Agent / swarm
# ---------------------------------------------------------------------------
# AGENT__ENABLED_AGENTS=["market","research"]
# AGENT__RECURSION_LIMIT=40
# AGENT__MAX_CONVERSATION_MESSAGES=100
# AGENT__SUPERVISOR_OUTPUT_MODE=last_message

# ---------------------------------------------------------------------------
# Persistence (checkpointer LangGraph)
# ---------------------------------------------------------------------------
# PERSISTENCE__BACKEND=memory          # memory | sqlite | postgres
# PERSISTENCE__SQLITE_PATH=./.suiswarm/checkpoints.sqlite
# PERSISTENCE__POSTGRES_DSN=postgresql://user:pass@localhost:5432/suiswarm

# ---------------------------------------------------------------------------
# Server (FastAPI / uvicorn)
# ---------------------------------------------------------------------------
# SERVER__HOST=0.0.0.0
# SERVER__PORT=8000
# SERVER__CORS_ORIGINS=["*"]
```

> Sau khi sửa `.env`, chạy `suiswarm config` để xác nhận các năng lực đã bật đúng như mong đợi.
