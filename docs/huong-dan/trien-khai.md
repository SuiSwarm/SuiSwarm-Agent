# Hướng dẫn triển khai

> Trạng thái: bản hướng dẫn vận hành · Ngôn ngữ: Tiếng Việt · Nhất quán với [`docs/REFACTORING_PLAN.md`](../REFACTORING_PLAN.md)
>
> Tài liệu này mô tả cách chạy **SuiSwarm Agent** — một swarm đa agent lấy Sui blockchain làm
> trọng tâm, xây trên LangGraph (supervisor + sub-agent ReAct). Có ba cách triển khai: **CLI**,
> **REST API**, và **Docker**. Thuật ngữ kỹ thuật giữ nguyên tiếng Anh khi đó là chuẩn ngành.

> **Phạm vi v1 (hiện tại):** swarm chạy bằng sub-agent **Market-data** (CoinGecko/GeckoTerminal)
> và **Research/Web** (Tavily). Sub-agent **Sui on-chain** chỉ được đăng ký khi biến
> `SUI_SERVICE__BASE_URL` có giá trị (service NestJS) — phần này tích hợp đầy đủ ở **Phase 8**
> (xem [§8 REFACTORING_PLAN](../REFACTORING_PLAN.md#7-lộ-trình-triển-khai-theo-phase)).

---

## Mục lục

1. [Yêu cầu & cài đặt](#1-yêu-cầu--cài-đặt)
2. [Cấu hình môi trường (.env)](#2-cấu-hình-môi-trường-env)
3. [Chạy CLI](#3-chạy-cli)
4. [Chạy REST API](#4-chạy-rest-api)
5. [Bảng endpoint & ví dụ curl](#5-bảng-endpoint--ví-dụ-curl)
6. [Chạy bằng Docker](#6-chạy-bằng-docker)
7. [Ghi chú về persistence](#7-ghi-chú-về-persistence)

---

## 1. Yêu cầu & cài đặt

- **Python**: 3.11 – 3.13 (môi trường dev khuyến nghị 3.13).
- **OpenAI API key**: bắt buộc (LLM mặc định là OpenAI).
- Các key tùy chọn theo năng lực muốn bật: CoinGecko, Tavily, Langfuse, service NestJS của Sui.

Cài đặt package (kèm nhóm dev để chạy test/lint):

```bash
python -m venv .venv
# Windows PowerShell:  .venv\Scripts\Activate.ps1
# Linux/macOS:         source .venv/bin/activate
pip install -e ".[dev]"
```

Sau khi cài, lệnh console `suiswarm` sẵn sàng dùng (entry point khai báo trong `pyproject.toml`).

---

## 2. Cấu hình môi trường (.env)

Cấu hình nạp qua `get_settings()` (pydantic-settings, có cache + `load_dotenv()`). Có hai nhóm biến:

**Bí mật — đặt theo tên quy ước (top-level):**

| Biến | Bắt buộc | Ý nghĩa |
|---|---|---|
| `OPENAI_API_KEY` | ✅ | Key cho LLM (provider mặc định OpenAI). |
| `COINGECKO_DEMO_API_KEY` (hoặc `COINGECKO_API_KEY`) | — | Bật tool thị trường (CoinGecko + GeckoTerminal). |
| `TAVILY_API_KEY` | — | Bật tool tìm kiếm web (Research agent). |
| `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL` | — | Bật tracing Langfuse. |

**Cấu hình có cấu trúc — dùng dấu phân tách `__` (model lồng):**

| Biến | Mặc định/ví dụ | Ý nghĩa |
|---|---|---|
| `LLM__PROVIDER` | `openai` | Provider LLM. |
| `LLM__MODEL` | (theo settings) | Tên model. |
| `LLM__BASE_URL` | — | Base URL nếu dùng endpoint tương thích. |
| `LLM__TEMPERATURE_WORKER` | — | Temperature cho sub-agent. |
| `HTTP__TIMEOUT` | — | Timeout HTTP client (giây). |
| `HTTP__MAX_RETRIES` | — | Số lần retry. |
| `HTTP__RATE_LIMIT_PER_MINUTE` | — | Giới hạn rate. |
| `SUI_SERVICE__BASE_URL` | — | URL REST của service NestJS; **có giá trị mới bật sub-agent Sui**. |
| `SUI_SERVICE__API_KEY` | — | API key gọi service NestJS. |
| `SUI_SERVICE__API_KEY_HEADER` | — | Tên header mang API key. |
| `AGENT__ENABLED_AGENTS` | `market,research` | Danh sách sub-agent bật. |
| `AGENT__RECURSION_LIMIT` | — | Recursion limit của graph. |
| `PERSISTENCE__BACKEND` | `memory` | `memory` \| `sqlite` \| `postgres`. |
| `PERSISTENCE__SQLITE_PATH` | — | Đường dẫn file SQLite (khi backend `sqlite`). |
| `PERSISTENCE__POSTGRES_DSN` | — | DSN Postgres (khi backend `postgres`). |
| `SERVER__HOST` | — | Host cho API server. |
| `SERVER__PORT` | `8000` | Port cho API server. |

> **Lưu ý kỹ thuật (bridge secret):** pydantic-settings **không** áp `validation_alias` cho field
> của model lồng, nên các secret theo tên quy ước (`OPENAI_API_KEY`, `COINGECKO_*`, `TAVILY_*`,
> `LANGFUSE_*`) được đọc ở field top-level rồi bridge vào model lồng bằng `model_validator`. Vì vậy
> bạn dùng đúng tên quy ước cho secret, và dùng tiền tố `__` cho các cấu hình còn lại.

Kiểm tra nhanh năng lực nào đang bật:

```bash
suiswarm config
```

Lệnh in bảng `LLM`, `CoinGecko`, `Tavily`, `Sui service (NestJS)`, `Langfuse` với trạng thái
`enabled`/`disabled` theo key đã cấu hình.

---

## 3. Chạy CLI

CLI dùng Typer, stream token của supervisor ra terminal. Có hai lệnh: `chat` và `config`.

**Cách gọi:**

```bash
# qua entry point
suiswarm chat

# hoặc qua module
python -m suiswarm_agent chat
```

**Chat một lượt (one-shot)** — truyền message làm tham số:

```bash
suiswarm chat "Giá BTC hiện tại là bao nhiêu?"
```

**Chat tương tác** — bỏ message, gõ `exit` hoặc `quit` để thoát:

```bash
suiswarm chat
```

**Các cờ của lệnh `chat`:**

| Cờ | Ý nghĩa |
|---|---|
| `--session-id` | Id hội thoại/thread (mặc định sinh tự động). |
| `--thread-id` | Alias của `--session-id` (LangGraph thread id). |
| `--user-id` | User id tùy chọn (dùng cho tracing). |
| `--model` | Override model LLM. |
| `--temperature` | Override temperature của worker. |
| `--stream` / `--no-stream` | Bật/tắt streaming token (mặc định bật). |
| `--log-level` | Mức log (mặc định `WARNING`). |

Ví dụ giữ ngữ cảnh xuyên lượt bằng thread id cố định (cần backend persistence khác `memory`
nếu muốn nhớ giữa các tiến trình — xem [§7](#7-ghi-chú-về-persistence)):

```bash
suiswarm chat "tóm tắt thị trường" --thread-id phien-001 --no-stream --log-level INFO
```

Kiểm tra cấu hình:

```bash
suiswarm config
```

---

## 4. Chạy REST API

API dùng FastAPI; vòng đời (`lifespan`) build graph cùng checkpointer. Chạy bằng uvicorn:

```bash
uvicorn suiswarm_agent.interfaces.api.app:app --host 0.0.0.0 --port 8000
```

> Host/port cũng có thể đặt qua `SERVER__HOST` / `SERVER__PORT`. Khi chạy qua uvicorn trực tiếp,
> dùng cờ `--host`/`--port` của uvicorn như trên.

Tài liệu OpenAPI tự sinh tại `http://localhost:8000/docs`.

---

## 5. Bảng endpoint & ví dụ curl

| Method | Endpoint | Mô tả | Body / Response |
|---|---|---|---|
| `POST` | `/chat` | Chat một lượt, trả lời đầy đủ. | Req: `{message, session_id?, user_id?}` · Res: `{answer, session_id}` |
| `POST` | `/chat/stream` | Chat streaming qua **SSE** (`text/event-stream`); stream token của supervisor. | Req: như `/chat` · Res: chuỗi sự kiện `data: {...}` |
| `GET` | `/healthz` | Health/readiness; trả về năng lực đang bật. | Res: `{status, capabilities}` |

Chi tiết request `/chat` và `/chat/stream`:

- `message` (string, bắt buộc, 1–8000 ký tự).
- `session_id` (string, tùy chọn; sinh tự động khi bỏ trống — dạng `api-<uuid>`).
- `user_id` (string, tùy chọn; dùng cho tracing).

**`POST /chat`:**

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Giá ETH hôm nay?", "session_id": "phien-001"}'
```

Phản hồi:

```json
{ "answer": "...", "session_id": "phien-001" }
```

**`POST /chat/stream` (SSE):**

```bash
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Tóm tắt thị trường crypto"}'
```

Luồng sự kiện trả về (mỗi dòng là một event SSE):

```text
data: {"token": "Thị "}
data: {"token": "trường "}
...
data: {"done": true, "session_id": "api-<uuid>"}
```

Nếu có lỗi domain, stream phát một event `data: {"error": "..."}`.

**`GET /healthz`:**

```bash
curl http://localhost:8000/healthz
```

Phản hồi:

```json
{ "status": "ok", "capabilities": { "llm": true, "coingecko": true, "tavily": false, "sui_service": false, "langfuse": false } }
```

> Lỗi domain (`SuiSwarmError`) ở `/chat` trả về HTTP `502` với `detail` là thông điệp lỗi.

---

## 6. Chạy bằng Docker

Repo có sẵn `Dockerfile` đa stage và `docker-compose.yml`.

**`Dockerfile` (đa stage):**

- Stage `builder`: build wheel từ `pyproject.toml` + `src/` để image runtime gọn.
- Stage `runtime`: cài wheel, chạy bằng user non-root (`appuser`, uid 10001), `EXPOSE 8000`, có
  `HEALTHCHECK` gọi `/healthz`.
- Lệnh mặc định: `uvicorn suiswarm_agent.interfaces.api.app:app --host 0.0.0.0 --port 8000`.

**`docker-compose.yml`:**

- Service `api`: build từ thư mục hiện tại, map cổng `8000:8000`, **đọc biến môi trường từ `.env`**
  (`env_file: .env`).
- Persistence mặc định là **SQLite** (chạy được ngay): đặt sẵn `PERSISTENCE__BACKEND=sqlite` và
  `PERSISTENCE__SQLITE_PATH=/data/checkpoints.sqlite`.
- **Volume** `suiswarm_data` mount vào `/data` để giữ file checkpoint qua các lần khởi động lại.
- `restart: unless-stopped`.

Chạy full stack local:

```bash
# tạo .env (ít nhất có OPENAI_API_KEY) rồi:
docker compose up --build
```

API sẽ phục vụ ở `http://localhost:8000` (thử `GET /healthz`).

> Để dùng **Postgres** cho môi trường hosted/đa người dùng: đổi `PERSISTENCE__BACKEND=postgres`,
> đặt `PERSISTENCE__POSTGRES_DSN`, và thêm một service `db` vào compose. Lưu ý phần đầu
> `docker-compose.yml`: cần cài một bản `langgraph-checkpoint-postgres` tương thích với
> `langgraph-checkpoint` đang dùng.

---

## 7. Ghi chú về persistence

Checkpointer của LangGraph được dựng qua `memory/checkpoint.py` (`build_checkpointer()` →
`InMemorySaver`; `checkpointer_context()` là async context manager hỗ trợ `memory`/`sqlite`/
`postgres`). Chọn backend bằng `PERSISTENCE__BACKEND`:

| Backend | Khi nào dùng | Ghi chú |
|---|---|---|
| `memory` | **Dev / CLI** | `InMemorySaver`; nhanh, không lưu giữa các tiến trình. Mặc định. |
| `sqlite` | **Một node** | Lưu vào file (`PERSISTENCE__SQLITE_PATH`); giữ hội thoại qua khởi động lại. Là mặc định trong `docker-compose.yml` (kèm volume). |
| `postgres` | **Hosted / đa người dùng** | Dùng `PERSISTENCE__POSTGRES_DSN`. Yêu cầu cài **package `langgraph-checkpoint-postgres` tương thích** với phiên bản `langgraph-checkpoint` đang dùng. |

Cả CLI lẫn API đều đi qua cùng cơ chế: mỗi hội thoại gắn với một `thread_id`
(CLI: `--session-id`/`--thread-id`; API: `session_id` trong body). Với backend `sqlite`/`postgres`,
dùng lại cùng `thread_id` sẽ tiếp tục đúng ngữ cảnh hội thoại trước.
