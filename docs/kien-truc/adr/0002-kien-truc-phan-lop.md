# ADR 0002 — Kiến trúc phân lớp ports-and-adapters

## Trạng thái

Accepted (Đã chấp thuận) · Ngày: 2026-06-03

## Bối cảnh

Scaffold ban đầu của SuiSwarm Agent đã tách lớp sơ bộ (`graph/`, `tools/`, `schemas`, `state`),
nhưng các mối quan tâm vẫn bị trộn lẫn. Điển hình là "god module" CoinGecko: một file gộp chung
HTTP client, logic nắn dữ liệu và 25 định nghĩa `@tool` cho hai API khác nhau (CoinGecko và
GeckoTerminal). Cấu hình thì bị xé lẻ qua nhiều cơ chế (`Settings`, env ngầm của
`langchain-tavily`, `os.getenv` thô cho Langfuse). Không có một HTTP client dùng chung, không có
cây exception domain, không có tầng logging.

Hệ quả: khó test (logic nghiệp vụ dính chặt vào thân `@tool` và lời gọi HTTP blocking), khó thay
thế nhà cung cấp (provider LLM hardcode), và khó mở rộng (thêm domain Sui, thêm sub-agent, thêm
giao diện API). Dự án cần một cấu trúc phụ thuộc rõ ràng, một chiều, để mỗi tầng có trách nhiệm
đơn nhất và có thể test/thay thế độc lập.

## Quyết định

Áp dụng **kiến trúc phân lớp theo phong cách ports-and-adapters**, với phụ thuộc **một chiều**
từ ngoài vào trong:

```
interfaces (CLI/API)  →  agent core (swarm)  →  tools (thin)  →  services (domain)  →  infra
```

Ánh xạ trực tiếp vào cấu trúc `src/suiswarm_agent/`:

- **interfaces** — `interfaces/cli/{app,render}.py` (Typer, streaming token của supervisor) và
  `interfaces/api/{app,routes,schemas,deps}.py` (FastAPI: `POST /chat`, `POST /chat/stream` SSE,
  `GET /healthz`). Đây là các adapter "driving" (điều khiển vào hệ thống).
- **agent core (swarm)** — `agent/`: `state.py`, `prompts.py`, `agents/{base,market,research,
  sui_onchain}.py` (build_worker_agent dùng `create_react_agent`), `supervisor.py`
  (`langgraph_supervisor.create_supervisor`), `graph.py` (`build_graph`, `make_graph`). Đây là
  lõi điều phối, không biết gì về transport HTTP cụ thể hay nhà cung cấp.
- **tools (thin)** — `tools/`: `base.py`, `registry.py` (đăng ký có điều kiện theo key cấu hình),
  và các `@tool` wrapper mỏng hướng LLM. **Logic nghiệp vụ không bao giờ nằm trong thân `@tool`.**
- **services (domain)** — tầng hàm domain + model có type cho từng API ngoài:
  `tools/market/coingecko/{client,service,models,tools}.py`,
  `tools/market/geckoterminal/{service,tools}.py`, `tools/sui/{client,service,tools}.py`,
  `tools/web/search.py`, `tools/system/builtin.py`. Mỗi service có **client** (transport),
  **service** (domain), **models** (DTO), và **tools** (wrapper).
- **infra (adapters "driven")** — hạ tầng dùng chung: `infra/http/client.py` (AsyncHttpClient:
  httpx async, retry+backoff bằng tenacity, AsyncRateLimiter, cache TTL tùy chọn, map lỗi),
  `infra/observability/langfuse.py`, `llm/factory.py` (`get_chat_model` đa provider qua
  `init_chat_model`), `memory/checkpoint.py` (checkpointer), `config/settings.py` (một Settings
  có type, lồng theo concern), `core/` (constants, exceptions, logging).

**Quy tắc bất biến:**

- Phụ thuộc chỉ đi từ ngoài vào trong; tầng trong **không** import tầng ngoài.
- Không module nào đọc `os.environ` trực tiếp — tất cả qua `get_settings()`.
- Tool là adapter mỏng trên service; service gọi client; client dùng `AsyncHttpClient` chung.

## Hệ quả

**Tích cực:**

- Mỗi tầng test được độc lập: service/client mock HTTP bằng `respx`; node mock LLM (LLM không bao
  giờ bị gọi thật trong test).
- Thay thế nhà cung cấp gọn gàng: provider LLM trừu tượng hóa qua `llm/factory.py`; transport HTTP
  tập trung ở `infra/http/client.py` (retry/rate-limit/cache wiring một lần).
- Mở rộng dễ: thêm tool/sub-agent/giao diện mới chỉ chạm tầng tương ứng, không lan rộng.
- Tách bạch giúp domain Sui cắm vào như một service nữa (xem ADR 0004) mà không phá vỡ lõi swarm.

**Tiêu cực / đánh đổi:**

- Nhiều file/lớp gián tiếp hơn (client → service → tool) so với một module gộp; có chi phí
  "ceremony" cho các trường hợp đơn giản.
- Cần kỷ luật review để không "đi tắt" (ví dụ nhét logic vào thân `@tool` hoặc đọc env trực tiếp).

**Trung tính:**

- Cầu nối cấu hình: pydantic-settings KHÔNG áp `validation_alias` cho field của model lồng, nên
  secret theo tên quy ước (ví dụ `OPENAI_API_KEY`) được đọc ở field top-level rồi bridge vào model
  lồng bằng `model_validator` — một chi tiết của tầng config cần được tôn trọng khi thêm setting.
