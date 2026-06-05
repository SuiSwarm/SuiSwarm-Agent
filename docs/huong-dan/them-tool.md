# Hướng dẫn: Thêm một tool mới

> Trạng thái: Tài liệu hướng dẫn · Ngôn ngữ: Tiếng Việt
>
> Tài liệu này mô tả cách thêm một **tool** mới cho SuiSwarm Agent đúng theo pattern hiện
> có. Mọi quy ước bám sát các quyết định D1-D6 và `docs/REFACTORING_PLAN.md`. Thuật ngữ kỹ
> thuật (tool, service, registry, envelope, respx...) giữ nguyên tiếng Anh khi đó là chuẩn
> ngành.

---

## 1. Tư tưởng kiến trúc (đọc trước khi code)

SuiSwarm tách rõ ba lớp cho mỗi domain tool. Khi thêm tool mới bạn đi đúng ba lớp này:

| Lớp | File | Trách nhiệm | Không được làm |
|---|---|---|---|
| **Service** | `<domain>/service.py` | Logic truy cập dữ liệu (async), gọi HTTP client, chuẩn hoá output | Không biết gì về LLM, không `@tool` |
| **Tool** | `<domain>/tools.py` | Wrapper `@tool` async **mỏng**, chỉ uỷ thác sang service | Không chứa logic nghiệp vụ |
| **Registry** | `tools/registry.py` | **Đăng ký có điều kiện** theo key cấu hình | Không import nặng ở top-level |

Lý do tách:

- Service test được độc lập bằng `respx` (mock httpx), **không cần** đụng tới LangChain/LLM.
- Tool chỉ là lớp "dịch" tham số cho LLM, nên giữ mỏng để đọc docstring là hiểu cách dùng.
- Registry quyết định tool có xuất hiện hay không **dựa trên cấu hình** (có key thì có tool,
  thiếu key thì nhóm tool vắng mặt) — tránh lỗi giữa chừng khi agent gọi tool không có credential.

Ví dụ chuẩn để bắt chước: `src/suiswarm_agent/tools/market/coingecko/`.

---

## 2. Bốn bước thêm một tool

### Bước 1 — Viết hàm trong `service.py` của domain

Mở service của domain tương ứng (ví dụ CoinGecko:
`src/suiswarm_agent/tools/market/coingecko/service.py`) và thêm một method async vào class
service. Method này:

- Validate/normalize tham số đầu vào (raise `ValueError` nếu thiếu bắt buộc).
- Gọi `self._client.get(...)` (HTTP client dùng chung đã có retry + backoff + rate limit).
- Bọc kết quả qua helper `base_response(endpoint, data, params)` để giữ envelope thống nhất.

```python
# src/suiswarm_agent/tools/market/coingecko/service.py
class CoinGeckoService:
    # ... các method có sẵn ...

    async def coin_tickers(self, coin_id: str, page: int = 1) -> dict[str, Any]:
        """Lấy danh sách ticker (cặp giao dịch) cho một coin id của CoinGecko."""
        cid = coin_id.strip().lower()
        if not cid:
            raise ValueError("coin_id is required.")
        params = {"page": max(page, 1), "order": "trust_score_desc"}
        endpoint = f"/coins/{_seg(cid)}/tickers"
        data = await self._client.get(endpoint, params)
        return base_response(endpoint, data, params)
```

Lưu ý theo pattern hiện có:

- Dùng `_seg(...)` để URL-encode mọi path segment do người dùng cung cấp.
- Dùng `_clamp(...)` để giới hạn các tham số kiểu số (per_page, max_points...).
- **Không** ném dữ liệu thô ra ngoài — luôn gói qua `base_response(...)` để có envelope
  (`source`, `endpoint`, `data`, ...).

### Bước 2 — Bọc `@tool` async mỏng trong `tools.py`

Mở `tools.py` của domain và thêm một wrapper `@tool`. Wrapper chỉ uỷ thác sang service,
**không** chứa logic:

```python
# src/suiswarm_agent/tools/market/coingecko/tools.py
@tool
async def coingecko_coin_tickers(coin_id: str, page: int = 1) -> dict:
    """Fetch trading pairs (tickers) for a CoinGecko coin id, ranked by trust score."""
    return await get_coingecko_service().coin_tickers(coin_id, page)
```

Sau đó thêm tool vào danh sách export ở cuối file:

```python
COINGECKO_TOOLS = [
    coingecko_search,
    # ... các tool có sẵn ...
    coingecko_nft_details,
    coingecko_coin_tickers,   # <-- thêm dòng này
]
```

Quy ước quan trọng:

- **Tên tool** theo prefix domain: `coingecko_*`, `geckoterminal_*`, `sui_*`...
- **Docstring viết bằng tiếng Anh** — đây là phần LLM đọc để chọn và gọi tool (prompt giữ
  tiếng Anh cho hiệu năng model; xem `agent/prompts.py`).
- Tham số dùng type hint rõ ràng; với tập giá trị cố định dùng `Literal[...]` như các tool
  hiện có (ví dụ `duration`, `days`).

### Bước 3 — Đăng ký trong `registry.py` (có điều kiện theo key)

Tool mới thuộc một nhóm domain đã có sẵn (`market`, `web`, `system`, `sui`). Nếu bạn chỉ
thêm tool vào `COINGECKO_TOOLS`/`GECKOTERMINAL_TOOLS`/`SUI_TOOLS`, nó **tự động** được
registry nhặt qua nhóm tương ứng — không cần sửa gì thêm. Đây là trường hợp phổ biến nhất.

Nhắc lại pattern đăng ký có điều kiện trong `tools/registry.py`: mỗi nhóm chỉ trả tool khi
credential tương ứng được cấu hình, và import được làm **lazy** (bên trong hàm) để import
module không kéo theo phụ thuộc nặng:

```python
# src/suiswarm_agent/tools/registry.py
def market_tools(settings: Settings | None = None) -> list[BaseTool]:
    """CoinGecko + GeckoTerminal tools (requires a CoinGecko Demo key)."""
    settings = settings or get_settings()
    if not settings.coingecko.enabled:        # <-- gate theo key cấu hình
        return []
    from suiswarm_agent.tools.market.coingecko.tools import COINGECKO_TOOLS
    from suiswarm_agent.tools.market.geckoterminal.tools import GECKOTERMINAL_TOOLS

    return [*COINGECKO_TOOLS, *GECKOTERMINAL_TOOLS]
```

Chỉ khi bạn tạo **một domain/nhóm tool hoàn toàn mới** (ví dụ một nguồn dữ liệu mới cần key
riêng) thì mới thêm một hàm nhóm mới và khai báo nó trong `available_tools(...)`:

```python
# Ví dụ: một nguồn mới cần credential riêng (myfeed)
def myfeed_tools(settings: Settings | None = None) -> list[BaseTool]:
    """MyFeed tools (requires a MyFeed key)."""
    settings = settings or get_settings()
    if not settings.myfeed.enabled:           # gate theo key cấu hình
        return []
    from suiswarm_agent.tools.market.myfeed.tools import MYFEED_TOOLS

    return list(MYFEED_TOOLS)


def available_tools(settings: Settings | None = None) -> dict[str, list[BaseTool]]:
    settings = settings or get_settings()
    return {
        "sui": sui_tools(settings),
        "market": market_tools(settings),
        "web": research_tools(settings),
        "system": system_tools(settings),
        "myfeed": myfeed_tools(settings),     # <-- nhóm mới
    }
```

Nếu thêm nhóm mới có credential riêng, nhớ khai báo settings tương ứng trong
`config/settings.py` (một model lồng có thuộc tính `enabled`) và, với secret theo tên quy
ước, bridge field top-level vào model lồng bằng `model_validator` (xem ghi chú lý do bridge
trong settings: pydantic-settings không áp `validation_alias` cho field của model lồng).

### Bước 4 — Viết test `respx`

Mỗi method service mới **phải** có test. Test chạy offline: mock httpx bằng `respx`, **không
bao giờ** gọi LLM thật. Đặt file trong `tests/unit/`. Dùng fixture `make_settings` đã có
trong `tests/conftest.py`.

```python
# tests/unit/test_coingecko_service.py
@respx.mock
async def test_coin_tickers_wraps_in_envelope(make_settings) -> None:
    respx.get(url__startswith=f"{BASE}/coins/").mock(
        return_value=httpx.Response(200, json={"tickers": [{"base": "BTC"}]})
    )
    out = await _service(make_settings).coin_tickers("bitcoin")
    assert out["source"] == "coingecko"
    assert out["endpoint"] == "/coins/bitcoin/tickers"
    assert out["data"]["tickers"][0]["base"] == "BTC"
```

Trong đó helper `_service(...)` đã có sẵn trong file test, dựng service với một
`CoinGeckoClient` từ settings có key giả:

```python
def _service(make_settings) -> CoinGeckoService:
    settings = make_settings(coingecko=CoinGeckoSettings(demo_api_key="test-key"))
    return CoinGeckoService(CoinGeckoClient(settings))
```

Nên test thêm:

- Trường hợp validate đầu vào (ví dụ `coin_id` rỗng phải raise `ValueError`).
- Nếu thêm nhóm tool mới: bổ sung assertion trong `tests/unit/test_registry.py` cho cả hai
  trạng thái — **có key** (tool xuất hiện) và **thiếu key** (nhóm trả `[]`). Khi đổi số lượng
  tool, cập nhật con số khẳng định (ví dụ `assert len(tools) == 25`).

---

## 3. Checklist trước khi mở PR

- [ ] Method async trong `service.py` (validate input, gọi client, gói `base_response`).
- [ ] Wrapper `@tool` async mỏng trong `tools.py`, đặt tên `<domain>_*`, docstring tiếng Anh.
- [ ] Tool đã được thêm vào danh sách export (`COINGECKO_TOOLS`/...) của domain.
- [ ] (Chỉ khi tạo nhóm mới) Hàm nhóm gate theo key + khai báo trong `available_tools(...)` +
      settings lồng tương ứng.
- [ ] Test `respx` cho service (offline, không gọi LLM); cập nhật `test_registry.py` nếu cần.
- [ ] Qua đủ cổng CI: `ruff check`, `ruff format --check`, `mypy`, `pytest`
      (hoặc chạy nhanh `make test`).

---

## 4. Tham chiếu nhanh

- Service mẫu: `src/suiswarm_agent/tools/market/coingecko/service.py`
- Tool mẫu (17 tool `coingecko_*`): `src/suiswarm_agent/tools/market/coingecko/tools.py`
- Tool dùng chung client qua `/onchain` (8 tool `geckoterminal_*`):
  `src/suiswarm_agent/tools/market/geckoterminal/`
- Registry có điều kiện: `src/suiswarm_agent/tools/registry.py`
- Tool Sui passthrough (chỉ đăng ký khi `SUI_SERVICE__BASE_URL` có):
  `src/suiswarm_agent/tools/sui/tools.py`
- Test mẫu `respx`: `tests/unit/test_coingecko_service.py`, `tests/unit/test_registry.py`
- Fixtures dùng chung: `tests/conftest.py`
