# Hướng dẫn: Dùng & đổi LLM provider

> Ngôn ngữ: Tiếng Việt · Nhất quán với [`docs/REFACTORING_PLAN.md`](../REFACTORING_PLAN.md)
>
> Tài liệu này giải thích cách chọn, đổi và mở rộng **LLM provider** trong SuiSwarm Agent.
> Toàn bộ việc chọn provider/model được điều khiển **qua cấu hình** (biến môi trường), nên
> **không phải sửa code call-site** khi đổi provider.

---

## 1. Nguyên tắc thiết kế

SuiSwarm Agent tách phần *chọn LLM* khỏi phần *dùng LLM*:

- **Một điểm tạo model duy nhất:** `src/suiswarm_agent/llm/factory.py`, hàm `get_chat_model(...)`.
- **Provider-agnostic:** factory dùng `init_chat_model` của LangChain. Provider (OpenAI /
  Anthropic / Azure / local OpenAI-compatible) được chọn **thuần từ cấu hình**, không hard-code.
- **Call-site không quan tâm provider:** supervisor và các sub-agent chỉ gọi `get_chat_model(role=...)`.
  Đổi provider chỉ là **đổi biến môi trường**, không sửa nơi gọi.

Hệ quả: thêm Anthropic/Azure/local là việc **cộng thêm cấu hình**, không phải refactor code.

---

## 2. Mặc định: OpenAI

Cấu hình mặc định (xem `config/settings.py`, lớp `LLMSettings`):

| Trường | Mặc định | Ghi chú |
|---|---|---|
| `provider` | `openai` | Định danh provider cho `init_chat_model`. |
| `model` | `gpt-4o-mini` | Tên model mặc định. |
| `base_url` | `None` | Chỉ dùng cho Azure / endpoint OpenAI-compatible / local. |
| `request_timeout` | `60.0` | Timeout mỗi request (giây). |
| `max_retries` | `2` | Số lần retry ở tầng client của LangChain. |

**Bí mật bắt buộc:** `OPENAI_API_KEY`. Nếu không có key, `get_chat_model(...)` raise
`ConfigError` với thông điệp nhắc đặt `OPENAI_API_KEY` (hoặc `LLM__API_KEY`) trong `.env`.

`.env` tối thiểu để chạy với OpenAI mặc định:

```dotenv
OPENAI_API_KEY=sk-...
```

---

## 3. Đổi provider / model qua biến môi trường

Cấu hình LLM dùng tiền tố lồng `LLM__` (dấu hai gạch dưới). Các biến chính:

| Biến môi trường | Trường tương ứng | Ý nghĩa |
|---|---|---|
| `LLM__PROVIDER` | `provider` | Tên provider, ví dụ `openai`, `anthropic`, `azure_openai`. |
| `LLM__MODEL` | `model` | Tên model, ví dụ `gpt-4o-mini`, `claude-3-5-sonnet-latest`. |
| `LLM__BASE_URL` | `base_url` | Endpoint tùy chỉnh: Azure / OpenAI-compatible / local. |
| `LLM__TEMPERATURE_SUPERVISOR` | `temperature_supervisor` | Nhiệt độ cho role `supervisor`. |
| `LLM__TEMPERATURE_WORKER` | `temperature_worker` | Nhiệt độ cho role `worker`. |
| `LLM__TEMPERATURE_DEFAULT` | `temperature_default` | Nhiệt độ cho role `default`. |

> **Mẹo về tiền tố model:** factory chấp nhận dạng `provider/model` (ví dụ
> `openai/gpt-4o-mini`). Nếu phần trước dấu `/` trùng với `provider` đang cấu hình, nó được
> cắt bỏ tự động (`_normalize_model`). Nên thường chỉ cần đặt `LLM__MODEL=gpt-4o-mini`.

Đổi model OpenAI (không đổi provider):

```dotenv
OPENAI_API_KEY=sk-...
LLM__MODEL=gpt-4o
```

---

## 4. Thêm provider mới (cộng thêm, không sửa call-site)

Vì factory dùng `init_chat_model`, thêm provider mới chỉ cần:

1. Cài package LangChain tương ứng (nếu chưa pin sẵn) — ví dụ `langchain-anthropic`.
2. Đặt biến môi trường `LLM__PROVIDER` + key của provider đó.

**Không** phải sửa `get_chat_model(...)` hay nơi gọi nó trong `agent/`. Đây là điểm cốt lõi:
mọi thay đổi là *cấu hình + (nếu cần) một dependency mới*, call-site giữ nguyên.

### 4.1. Anthropic

```dotenv
LLM__PROVIDER=anthropic
LLM__MODEL=claude-3-5-sonnet-latest
ANTHROPIC_API_KEY=sk-ant-...
```

> Lưu ý: bí mật `OPENAI_API_KEY` được đọc ở field top-level rồi bridge vào `LLMSettings.api_key`.
> Với provider khác, đặt key theo quy ước của provider đó (ví dụ `ANTHROPIC_API_KEY`) để
> `init_chat_model` tự nhận, hoặc đặt trực tiếp `LLM__API_KEY` cho field lồng.

### 4.2. Azure OpenAI

Azure cần endpoint riêng, đặt qua `LLM__BASE_URL`:

```dotenv
LLM__PROVIDER=azure_openai
LLM__MODEL=<tên-deployment>
LLM__BASE_URL=https://<resource>.openai.azure.com/
LLM__API_KEY=<azure-key>
```

### 4.3. Local / OpenAI-compatible (vLLM, Ollama, LM Studio…)

Dùng provider `openai` nhưng trỏ `base_url` về endpoint local OpenAI-compatible:

```dotenv
LLM__PROVIDER=openai
LLM__MODEL=<tên-model-local>
LLM__BASE_URL=http://localhost:11434/v1
OPENAI_API_KEY=local-not-used-but-required
```

> `base_url` chỉ được truyền vào `init_chat_model` khi có giá trị; bỏ trống thì dùng endpoint
> mặc định của provider.

---

## 5. Temperature theo role (supervisor / worker / default)

Mỗi role có một nhiệt độ riêng để supervisor điều phối **tất định** còn worker được phép
sáng tạo hơn một chút:

| Role | Trường | Mặc định | Vai trò |
|---|---|---|---|
| `supervisor` | `temperature_supervisor` | `0.0` | Điều phối/routing — cần tất định. |
| `worker` | `temperature_worker` | `0.2` | Sub-agent ReAct — hơi sáng tạo. |
| `default` | `temperature_default` | `0.3` | Khi không chỉ định role cụ thể. |

Khi gọi `get_chat_model(role="supervisor")`, factory tự tra nhiệt độ tương ứng. Có thể ghi đè:

- **Toàn cục theo role:** đặt `LLM__TEMPERATURE_SUPERVISOR` / `LLM__TEMPERATURE_WORKER` /
  `LLM__TEMPERATURE_DEFAULT` trong `.env`.
- **Theo lời gọi:** truyền `temperature=` (và/hoặc `model=`) trực tiếp vào `get_chat_model(...)`;
  giá trị truyền vào thắng cấu hình theo role.

Ví dụ giảm nhiệt độ worker để bớt ngẫu nhiên:

```dotenv
LLM__TEMPERATURE_WORKER=0.0
```

---

## 6. API của factory

```python
get_chat_model(
    role="supervisor" | "worker" | "default",   # mặc định "default"
    *,
    model: str | None = None,        # ghi đè LLM__MODEL
    temperature: float | None = None,  # ghi đè nhiệt độ theo role
    **overrides,                     # truyền thẳng vào init_chat_model
) -> BaseChatModel
```

Hành vi cần nhớ:

- Thiếu key → raise `ConfigError`.
- Không khởi tạo được provider/model → raise `LLMError`.
- `**overrides` được merge sau cùng, nên có thể truyền thêm tham số đặc thù provider khi cần.

---

## 7. Kiểm tra nhanh sau khi đổi

- `make config` / lệnh `config` của CLI để xem `capabilities()` và cấu hình LLM đang áp dụng.
- Chạy test factory: `pytest tests/unit/test_llm_factory.py` (LLM **không** bị gọi thật trong
  test — xem [kiem-thu.md](./kiem-thu.md)).

---

## Tóm tắt

- Một điểm tạo model: `llm/factory.py::get_chat_model`.
- Đổi provider/model = đổi `LLM__PROVIDER` / `LLM__MODEL` / `LLM__BASE_URL`, **không** sửa call-site.
- Mặc định OpenAI (`gpt-4o-mini`), cần `OPENAI_API_KEY`.
- Thêm Anthropic / Azure / local là **cộng thêm cấu hình + dependency**, không refactor.
- Temperature tách theo role: supervisor (0.0) / worker (0.2) / default (0.3), ghi đè được qua env hoặc tham số.
