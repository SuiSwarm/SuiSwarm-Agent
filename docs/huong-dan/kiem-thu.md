# Hướng dẫn: Kiểm thử (Testing)

> Ngôn ngữ: Tiếng Việt · Nhất quán với [`docs/REFACTORING_PLAN.md`](../REFACTORING_PLAN.md)
>
> Tài liệu này mô tả **chiến lược test** của SuiSwarm Agent: bộ công cụ, bố cục thư mục, cách
> mock HTTP, nguyên tắc **không bao giờ gọi LLM thật**, các fixtures dùng chung, và **cổng chất
> lượng** mà CI bắt buộc.

---

## 1. Bộ công cụ test

| Công cụ | Vai trò |
|---|---|
| `pytest` | Test runner chính. |
| `pytest-asyncio` | Hỗ trợ test async; cấu hình `asyncio_mode = "auto"`. |
| `respx` | Mock tầng HTTP của `httpx` (chặn mọi request mạng thật ra ngoài). |
| `coverage` | Đo độ phủ; bật `branch = true`, nguồn `src/suiswarm_agent`. |

Cấu hình pytest (trong `pyproject.toml`, `[tool.pytest.ini_options]`):

- `testpaths = ["tests"]`
- `asyncio_mode = "auto"` — không cần đánh dấu `@pytest.mark.asyncio` cho từng test async.
- `addopts = "-q --strict-markers"` — chế độ gọn, marker chưa khai báo sẽ báo lỗi.
- Marker `e2e`: test chạm API ngoài thật, **bỏ qua mặc định trong CI**.

---

## 2. Bố cục thư mục

```
tests/
├── conftest.py            # fixtures dùng chung (autouse + factory)
├── unit/                  # test đơn vị: service, client, registry, settings, factory…
│   ├── test_coingecko_service.py
│   ├── test_geckoterminal_service.py
│   ├── test_http_client.py
│   ├── test_llm_factory.py
│   ├── test_registry.py
│   ├── test_settings.py
│   └── test_sui.py
└── integration/           # test ráp nối: dựng graph, luồng end-to-end nội bộ
    └── test_graph.py
```

- **`tests/unit`** — kiểm thử từng thành phần cô lập: HTTP client (retry/error mapping),
  service CoinGecko/GeckoTerminal, đăng ký tool có điều kiện (`registry`), `Settings`,
  `llm/factory`, tool Sui.
- **`tests/integration`** — kiểm thử lắp ghép, ví dụ dựng `build_graph(...)` và xác nhận
  graph/agent cấu hình đúng mà vẫn **không** gọi LLM hay mạng thật.

---

## 3. Mock HTTP với respx

Mọi tương tác mạng đi qua `httpx` (CoinGecko, GeckoTerminal, service Sui NestJS) được mock
bằng `respx`. Không có request thật nào rời máy trong test.

Mẫu chuẩn — đánh dấu `@respx.mock` và khai báo route:

```python
import httpx
import respx

from suiswarm_agent.core.exceptions import RateLimitedError, UpstreamAPIError
from suiswarm_agent.infra.http.client import AsyncHttpClient


@respx.mock
async def test_retry_then_success(fast_http) -> None:
    route = respx.get("https://svc.test/ping").mock(
        side_effect=[httpx.Response(503), httpx.Response(200, json={"ok": True})]
    )
    client = AsyncHttpClient(
        "https://svc.test", settings=fast_http(max_retries=3), service_name="svc"
    )
    assert await client.get_json("/ping") == {"ok": True}
    assert route.call_count == 2
```

Mẫu này cũng minh họa cách test các nhánh quan trọng của `AsyncHttpClient`:

- **Retry rồi thành công** — `side_effect` trả 503 rồi 200, kiểm `call_count`.
- **Lỗi client → `UpstreamAPIError`** — trả 404, assert `exc.status_code == 404`.
- **429 cạn retry → `RateLimitedError`** — trả 429 nhiều lần, kiểm tổng số lần gọi.
- **Tham số `None` bị bỏ** — xác nhận query param `None` không lọt vào URL.

> Vì test dùng `fast_http` (backoff = 0, rate-limit tắt), retry **không sleep**, test chạy nhanh.

---

## 4. Không bao giờ gọi LLM thật

Đây là quy tắc cứng: **LLM không bao giờ bị gọi thật trong test.** Cách đảm bảo:

- Fixture autouse `_isolated_settings` đặt `OPENAI_API_KEY=sk-test-dummy` — đủ để vượt kiểm
  tra key trong `get_chat_model(...)` nhưng **không** dùng key thật.
- Test `factory` chỉ kiểm hành vi cấu hình (chọn provider/model, raise `ConfigError` khi thiếu
  key, áp nhiệt độ theo role) — **không** thực sự gọi tới nhà cung cấp model.
- Test integration dựng graph và kiểm cấu trúc/cấu hình; không phát sinh inference thật.

Hệ quả: test chạy **offline**, tất định, không tốn chi phí API và không phụ thuộc mạng.

---

## 5. Fixtures dùng chung (`tests/conftest.py`)

### 5.1. `_isolated_settings` (autouse)

Chạy tự động cho **mọi** test, đảm bảo môi trường sạch và tất định:

- Đặt `OPENAI_API_KEY=sk-test-dummy`.
- **Xóa** các biến có thể rò từ máy host: `TAVILY_API_KEY`, `COINGECKO_DEMO_API_KEY`,
  `COINGECKO_API_KEY`, `SUI_SERVICE__BASE_URL` — để các test assert "capability bị tắt" không
  bị nhiễu bởi cấu hình của máy đang chạy.
- Gọi `get_settings.cache_clear()` **trước và sau** mỗi test, vì `get_settings()` có cache.

> Nhờ vậy, test về đăng ký tool có điều kiện (`registry`) hay `capabilities()` luôn cho kết quả
> ổn định bất kể `.env` trên máy.

### 5.2. `fast_http`

Factory tạo `HTTPSettings` **không ngủ**: `rate_limit_per_minute=0`, `backoff_base=0.0`,
`backoff_max=0.0`. Cho phép ghi đè qua tham số (ví dụ `fast_http(max_retries=3)`). Dùng cho mọi
test chạm HTTP client để retry không làm chậm bộ test.

### 5.3. `make_settings`

Factory tạo `Settings` hoàn chỉnh, mặc định gắn `http=fast_http()` (HTTP không sleep) và
**bỏ qua `.env` của host** (`_env_file=None`) để tất định. Nhận `**overrides` để tùy biến từng
test.

---

## 6. Cổng chất lượng (CI gate)

CI bắt buộc các bước sau (xem `Makefile` và `pyproject.toml`):

| Bước | Lệnh | Mục đích |
|---|---|---|
| Lint | `ruff check .` | Bắt lỗi style/bug pattern. |
| Format | `ruff format --check` | Đảm bảo định dạng nhất quán (chế độ kiểm tra, không sửa). |
| Type | `mypy` | Kiểm tra kiểu tĩnh (strict: `disallow_untyped_defs`, plugin pydantic). |
| Test | `pytest` | Chạy toàn bộ test. |

Lệnh tổng hợp:

```bash
make check     # = lint + type + test (đúng cổng CI)
make test      # chỉ chạy pytest
make cov       # pytest --cov (báo cáo độ phủ)
pytest         # chạy trực tiếp
```

> `make check` trong Makefile chạy `lint type test`. Bước `ruff format --check` là phần của
> cổng CI; chạy cục bộ bằng `ruff format --check .` (hoặc `make format` để **tự sửa** định dạng).

Ghi chú cấu hình:

- **mypy**: target `py311`, `packages=["suiswarm_agent"]`, `mypy_path=src`, bật
  `disallow_untyped_defs` / `check_untyped_defs` / `no_implicit_optional`; thư viện thiếu stub
  (langgraph, langchain, langfuse…) được `ignore_missing_imports`; test được nới
  `disallow_untyped_defs=false`.
- **ruff**: `line-length=100`, target `py311`, rule set `E,F,I,UP,B,C4,SIM,RUF`; giữ thông điệp
  tiếng Việt (bỏ qua `RUF001/002/003` về unicode mơ hồ).

---

## 7. Quy ước viết test mới

- Đặt test đơn vị vào `tests/unit`, test ráp nối vào `tests/integration`.
- Test async: cứ viết `async def test_...` — `asyncio_mode=auto` lo phần còn lại.
- Mọi truy cập mạng phải qua `@respx.mock`; **không** gọi mạng thật (trừ test gắn marker `e2e`).
- Dùng `fast_http` / `make_settings` thay vì tự dựng `Settings`/`HTTPSettings` thủ công.
- Không khởi tạo LLM thật; chỉ kiểm hành vi cấu hình của `get_chat_model`.
- Test phụ thuộc capability (tool đăng ký có điều kiện) dựa trên môi trường đã được
  `_isolated_settings` dọn sạch.

---

## Tóm tắt

- Stack: `pytest` + `pytest-asyncio` (`asyncio_mode=auto`) + `respx` + `coverage`.
- Bố cục: `tests/unit` (cô lập) và `tests/integration` (ráp nối).
- HTTP mock bằng `respx`; **LLM không bao giờ gọi thật** (key dummy + chỉ test cấu hình).
- Fixtures: `make_settings`, `fast_http`, và autouse `_isolated_settings`.
- Cổng chất lượng: `ruff check` + `ruff format --check` + `mypy` + `pytest`; tổng hợp qua `make check`.
