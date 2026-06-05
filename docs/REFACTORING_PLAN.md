# SuiSwarm Agent — Kế hoạch Refactor & Kiến trúc

> Trạng thái: **Bản nháp để review** · Ngày: 2026-06-03 · Ngôn ngữ: Tiếng Việt
>
> Tài liệu này là nguồn chân lý duy nhất cho việc chuyển scaffold hiện tại thành một dự án
> **chuẩn production, có cấu trúc chuyên nghiệp**. Bố cục: **(1)** hiện trạng → **(2)** danh
> mục vấn đề → **(3)** kiến trúc mục tiêu → **(4)** cấu trúc thư mục → **(5)** tiêu chuẩn
> xuyên suốt → **(6)** lộ trình theo phase → **(7)** chiến lược migration → **(8)** quyết định.
>
> Chưa có gì được triển khai trong code. Đây là bản thiết kế để thống nhất trước khi code.

---

## 0. Các quyết định đã chốt (định hình toàn bộ plan)

Bốn quyết định nền tảng đã được chủ dự án xác nhận, mọi phần bên dưới đều bám theo:

| # | Quyết định | Lựa chọn đã chốt | Hệ quả chính |
|---|---|---|---|
| D1 | **Định hướng sản phẩm** | **Sui-first on-chain** | Sui blockchain là **domain lõi** (RPC, on-chain, DeFi, portfolio). Market data (CoinGecko/GeckoTerminal) thành **phụ trợ**. |
| D2 | **Mô hình agent** | **Multi-agent swarm** | Một **supervisor** điều phối nhiều **sub-agent** chuyên biệt; mỗi sub-agent là một agent ReAct tự chain được tool của mình. |
| D3 | **Giao diện / triển khai** | **CLI + REST API + Docker** | Có cả CLI (streaming) và **FastAPI service** (`/chat`, `/healthz`), kèm **container hóa** để host. |
| D4 | **Ngôn ngữ tài liệu** | **Tiếng Việt** | Toàn bộ `docs/` viết bằng tiếng Việt; thuật ngữ kỹ thuật giữ nguyên tiếng Anh khi đó là chuẩn ngành. |
| D5 | **Triển khai Sui** | **Service NestJS riêng** | Mọi tương tác Sui (RPC, giữ key, ký tx) nằm ở service NestJS tách biệt. Python **gọi qua REST API**; `tools/sui/*` chỉ là HTTP client mỏng. |
| D6 | **Quyền agent với Sui** | **Full (đọc + ghi), không gate ở Python** | Agent dùng key riêng (NestJS giữ); guardrail do repo *policy contract* riêng lo. Repo này chỉ **log/trace** hành động ghi để audit. |

> Định danh sản phẩm sau khi chốt: **SuiSwarm Agent = một "đàn" (swarm) các AI agent chuyên
> biệt, lấy Sui blockchain làm trọng tâm, do một supervisor điều phối.** Tên gọi giờ khớp với
> thực tế: *Sui* (chain lõi) + *Swarm* (đa agent).
>
> **Phạm vi trước mắt (v1):** service NestJS *chưa được dựng*, nên agent v1 chạy bằng tool
> **phân tích thị trường (CoinGecko/GeckoTerminal) + tìm kiếm web (Tavily)**. Phần Sui được
> **chuẩn bị sẵn chỗ cắm** và tích hợp ở **Phase 8** khi NestJS sẵn sàng. Tài liệu vẫn mô tả
> kiến trúc đích đầy đủ để chuẩn bị đúng hướng.

---

## Mục lục

1. [Tóm tắt điều hành](#1-tóm-tắt-điều-hành)
2. [Hiện trạng dự án](#2-hiện-trạng-dự-án)
3. [Danh mục vấn đề](#3-danh-mục-vấn-đề)
4. [Kiến trúc mục tiêu](#4-kiến-trúc-mục-tiêu-sui-first-swarm)
5. [Cấu trúc thư mục mục tiêu](#5-cấu-trúc-thư-mục-mục-tiêu)
6. [Tiêu chuẩn xuyên suốt](#6-tiêu-chuẩn-xuyên-suốt)
7. [Lộ trình triển khai theo phase](#7-lộ-trình-triển-khai-theo-phase)
8. [Chiến lược migration & các quyết định còn lại](#8-chiến-lược-migration--các-quyết-định-còn-lại)
9. [Phụ lục — Quick wins & Definition of Done](#9-phụ-lục)

---

## 1. Tóm tắt điều hành

SuiSwarm Agent hiện là một **scaffold chạy được nhưng còn ở giai đoạn sớm**: một agent
LangGraph chạy một lượt (`plan → execute_tools → respond`) qua CLI Typer, với ~28 tool dữ liệu
thị trường crypto, tracing Langfuse và bộ test mỏng. Nền tảng tốt (Python có type, layout
`src/`, pydantic-settings, đã tách `graph`/`tools`/`schemas`), nhưng **chưa đạt chuẩn
production**.

Theo các quyết định đã chốt ([§0](#0-các-quyết-định-đã-chốt-định-hình-toàn-bộ-plan)), dự án sẽ
được tái cấu trúc thành **một swarm đa agent lấy Sui làm trọng tâm**, phục vụ qua **cả CLI và
REST API**, đóng gói **Docker**. Những thay đổi lớn nhất:

- **Lấp khoảng trống định danh** — thêm domain **Sui on-chain (lõi)** và **kiến trúc swarm
  (supervisor + sub-agent)** để tên gọi khớp thực tế.
- **Phá vỡ sự cứng nhắc kiến trúc** — mỗi sub-agent là agent ReAct **tự chain được tool phụ
  thuộc** (vd: tìm coin → lấy chi tiết); thực thi **bất đồng bộ & song song**; **provider LLM
  trừu tượng hóa** (không hardcode OpenAI).
- **Phân lớp tool stack** — tách "god module" CoinGecko 593 dòng thành các lớp **client /
  service / models / tools**, dùng chung **HTTP client có retry / rate-limit / cache**.
- **Hợp nhất cấu hình** về một `Settings` có type duy nhất.
- **Siết vệ sinh kỹ thuật** — một nguồn dependency + lock file, CI/CD, ruff/mypy/pytest,
  logging có cấu trúc, LICENSE, và test thật (có mock HTTP/LLM).

Lộ trình gồm **8 phase**, chạy tăng dần, **không làm hỏng CLI đang chạy** ở mỗi bước.

---

## 2. Hiện trạng dự án

### 2.1 Cái đang có

| Mảng | Hiện trạng |
|---|---|
| Điều phối | LangGraph `StateGraph`: `START → plan → {execute_tools \| respond} → respond → END` |
| Planner | LLM `with_structured_output(PlanDecision)`; chọn 1–5 bước tool **trước** khi chạy |
| Executor | Vòng `for` **đồng bộ**; mỗi bước `tool.invoke(...)` |
| Responder | LLM tổng hợp câu trả lời từ `plan` + `tool_results` (nhồi repr thô vào prompt) |
| Tools | 17 CoinGecko + 8 GeckoTerminal + Tavily + `get_utc_time` + `describe_project` |
| Giao diện | CLI Typer (`suiswarm chat`), interactive + one-shot, nhớ 100 message trong RAM |
| Cấu hình | `pydantic-settings` (chỉ OpenAI + CoinGecko) |
| Observability | Langfuse callback (tùy chọn) |
| Test | 3 file `unittest` (chuẩn hóa settings, wiring graph, trim CLI) |
| Đóng gói | `pyproject.toml` (setuptools) + `requirements.txt` **trùng lặp**; entry point `suiswarm` |

### 2.2 Tech stack

Python ≥3.11 (máy local đang chạy **3.13.3**), LangGraph, langchain-core, langchain-openai,
langchain-tavily, Langfuse 3.x, httpx, pydantic-settings, Typer, Rich.

### 2.3 Cái đang tốt (giữ lại)

- Layout `src/`, package cài đặt được, có console entry point.
- Đã tách lớp sơ bộ: `graph/`, `tools/`, `schemas.py`, `state.py`, `prompts.py`.
- Code có type, planner xuất structured output qua Pydantic, có registry + catalog tool.
- Langfuse tùy chọn, import lazy (không crash khi chưa cấu hình).
- Đã có vài xử lý "demo-safe": lấy mẫu chart, fallback `top_movers` khi key demo không gọi
  được `/coins/top_gainers_losers`.

---

## 3. Danh mục vấn đề

Mức độ: 🔴 Cao (chặn production / đúng đắn / scale) · 🟡 Trung bình (chất lượng / bảo trì) · 🟢 Thấp (hoàn thiện).

### 3.1 Sản phẩm & định danh

- 🔴 **Tên không khớp thực tế.** "SuiSwarm" ngụ ý *Sui + swarm*, nhưng code **không có tool Sui
  và không có đa agent**. → Đã được giải quyết bằng quyết định D1+D2; phần còn lại của plan
  hiện thực hóa điều đó.
- 🟡 **Chưa có mô tả mục đích / người dùng / phi mục tiêu.** README mới chỉ là hướng dẫn cài đặt.

### 3.2 Kiến trúc agent

- 🔴 **Không chain được tool phụ thuộc.** `plan_request` (`graph/nodes.py:32`) lên kế hoạch
  *toàn bộ* bước tool **trước khi chạy bất kỳ tool nào**, rồi `execute_tools` chạy mù. Không
  làm được "search → dùng ID trả về → lấy chi tiết" — đúng thứ mà `coingecko_search` sinh ra
  để phục vụ. **Không có vòng lặp** quay lại planner.
- 🔴 **Thực thi tuần tự, đồng bộ.** `execute_tools` (`graph/nodes.py:81`) là vòng `for` gọi
  `httpx.get` blocking. Các bước độc lập (vd "giá BTC" + "trending pools") chạy nối tiếp. Không
  async, không song song.
- 🟡 **Truyền context thô.** `respond` (`graph/nodes.py:135`) nhồi repr Pydantic + JSON tool
  đầy đủ (`f"...{plan}...{tool_results}"`) vào prompt. Tốn token, dễ vỡ, lộ repr object Python
  cho model. Không tóm tắt/cắt ngắn (trừ lấy mẫu chart).
- 🟡 **Nhồi lại toàn bộ hội thoại mỗi lượt.** `_format_conversation` đổ tới 100 message vào
  **cả** prompt planner lẫn responder mỗi lần gọi. Không có chiến lược memory (windowing/tóm tắt).
- 🟡 **Không dùng persistence của LangGraph.** `build_graph()` compile **không checkpointer**;
  CLI tự nối message thủ công. Không `thread_id`, không resume, không lưu xuyên phiên.
- 🟢 **Magic number rải rác** (`MAX_TOOL_STEPS=5`, `CONVERSATION_CONTEXT_LIMIT=100`,
  `SESSION_MESSAGE_LIMIT=100`) thay vì gom vào config.

### 3.3 Tầng LLM

- 🔴 **Provider hardcode OpenAI.** `build_chat_model` (`llm.py`) trả `ChatOpenAI`; `Settings`
  chỉ mô hình hóa OpenAI. Đổi sang Anthropic/Claude, Azure, model local đều phải sửa code.
  Không cấu hình được model/temperature riêng cho từng node.
- 🟢 **Thay đổi local chưa commit** đang đổi temperature mặc định `0.2 → 0.6` trong `llm.py` —
  một giá trị cấu hình sống trong code, đang nằm ở diff chưa review.

### 3.4 Tầng tool

- 🔴 **"God module" CoinGecko.** `tools/coingecko.py` dài **593 dòng / 25 tool**, trộn lẫn HTTP
  client (`_get`, `_auth_headers`), nắn dữ liệu (`_base_response`, `_sample_*`), và 25 định
  nghĩa `@tool` cho **hai API khác nhau** (CoinGecko *và* GeckoTerminal).
- 🔴 **Không có khả năng chịu lỗi HTTP.** `_get` (`tools/coingecko.py:20`) là gọi đồng bộ một
  phát: **không retry, không backoff, không rate limit, không cache, không client/pool dùng
  chung.** Tier demo của CoinGecko giới hạn rất gắt → user gặp lỗi 429.
- 🟡 **Nhồi cả catalog 28 tool vào prompt planner mỗi lượt.** `render_tool_catalog` đổ **toàn
  bộ JSON schema** từng tool vào system prompt mỗi turn — tốn token, khó chọn tool. Không nhóm/
  namespace/định tuyến.
- 🟡 **Tool đăng ký vô điều kiện.** Tool crypto vẫn đăng ký dù thiếu `COINGECKO_DEMO_API_KEY`;
  lỗi chỉ lộ ra giữa lúc chạy dưới dạng string. `tools/search.py` khởi tạo `TavilySearch()`
  **ngay lúc import** (side effect) và gọi `load_dotenv()` lúc import — dễ vỡ nếu thiếu key.
- 🟡 **Nội suy path không escape.** `network` / `contract_address` do người dùng nhập được
  nhét thẳng vào path URL (vd `f"/coins/{platform}/contract/{address}"`), không encode/validate.
- 🟢 **Tool đồ chơi** (`get_utc_time`, `describe_project`) đang là "công dân hạng nhất".

### 3.5 Cấu hình

- 🔴 **Ba cơ chế config cạnh tranh.** `Settings` chỉ mô hình OpenAI + CoinGecko; Tavily được
  `langchain-tavily` đọc ngầm từ env; Langfuse đọc qua `os.getenv` thô trong `observability.py`.
  Không có một bề mặt config có type duy nhất.
- 🟡 **`load_dotenv()` gọi ở 3+ nơi** (`settings.py`, `observability.py`, `tools/search.py`) và
  gọi **mỗi lần** `is_langfuse_configured()`.
- 🟡 **Giá trị vận hành hardcode** (timeout=20s, `max_results=5`, base URL, temperature từng
  node) không cấu hình được.

### 3.6 Xử lý lỗi, logging & observability

- 🔴 **Không có logging.** Codebase dùng 0 `logging`; chẩn đoán đẩy ra stdout qua Rich
  (`console.print`) hoặc bị nuốt. Không log level, không log có cấu trúc, không correlation id.
- 🟡 **`except Exception` quá rộng** ở `cli.py` và `execute_tools`, stringify tất cả; không có
  cây exception domain. Text lỗi thô từ API upstream (`exc.response.text`) bị lộ ra cho user.
- 🟢 **Langfuse là telemetry duy nhất**; không metrics, không tín hiệu health/readiness.

### 3.7 Kiểm thử & cổng chất lượng

- 🔴 **Test mỏng, nông.** 3 file `unittest` chỉ phủ wiring/chuẩn hóa. **Không test tool, không
  mock HTTP, không mock LLM ở mức node, không test end-to-end.**
- 🔴 **Không có CI/CD.** Không `.github/workflows`, không tự động lint/type/test khi mở PR.
- 🟡 **Không có config linter/formatter/type-check.** `.gitignore` có nhắc `.ruff_cache` /
  `.mypy_cache` (đã có ý định) nhưng **không có cấu hình ruff/mypy/black** trong `pyproject.toml`.
- 🟡 **Không đo coverage, không pre-commit hook.**

### 3.8 Đóng gói & vệ sinh repo

- 🔴 **Dependency trùng lặp, không lock file.** `requirements.txt` lặp lại danh sách của
  `pyproject.toml` (sẽ lệch nhau theo thời gian); không pin/lock version để cài tái lập được.
- 🔴 **Dependency trực tiếp chưa khai báo.** `openai` (`cli.py:4`), `pydantic` (`schemas.py:3`),
  `typing_extensions` (`state.py:5`) được import trực tiếp nhưng chỉ tồn tại gián tiếp.
- 🟡 **Không có nhóm dev-dependency**, không `Makefile`/task runner, không marker `py.typed`.
- 🟡 **Version trùng lặp** ở `pyproject.toml` và `__init__.py` (hai nguồn chân lý).
- 🟡 **Thiếu `LICENSE`, `CHANGELOG.md`, `CONTRIBUTING.md`, `.python-version`.**
- 🟡 **Chưa có container hóa / câu chuyện triển khai** ngoài dev server của LangGraph CLI.
  *(Quyết định D3 đưa Docker + API vào phạm vi.)*

### 3.9 CLI / UX

- 🟡 **Không streaming** — `graph.invoke` block rồi in message cuối; UX chat kém. Chưa dùng
  streaming của LangGraph/LangChain.
- 🟡 **Không persistence xuyên lần chạy**, không cờ `--model` / `--temperature`, không render
  đẹp kết quả có cấu trúc (bảng cho dữ liệu thị trường, v.v.).

### 3.10 Tài liệu

- 🟡 **Docs sơ sài** — README (cài đặt) + `ARCHITECTURE.md` mỏng. Không có tham chiếu cấu hình,
  hướng dẫn "thêm tool/provider/sub-agent", hướng dẫn triển khai, ADR, hướng dẫn đóng góp.

---

## 4. Kiến trúc mục tiêu (Sui-first Swarm)

### 4.1 Nguyên tắc

1. **Phân lớp (ports-and-adapters).** Phụ thuộc một chiều: **interfaces (CLI/API)** →
   **agent core (swarm)** → **tools (thin)** → **services (domain)** → **infrastructure
   (HTTP / LLM provider / observability / persistence / config)**.
2. **Tool là adapter mỏng trên service.** Mỗi API ngoài có **client** (transport), **service**
   (hàm domain + model có type), và **`@tool` wrapper** (hướng LLM, mỏng). Logic nghiệp vụ
   **không bao giờ** nằm trong thân `@tool`.
3. **Mọi thứ cấu hình được nằm trong một `Settings` có type** (lồng theo từng concern); code
   đọc config, không đọc `os.environ` trực tiếp.
4. **Factory LLM trừu tượng hóa provider** (OpenAI/Anthropic/Azure/local), override theo từng
   vai (supervisor / sub-agent / responder).
5. **I/O bất đồng bộ** với HTTP client dùng chung có retry/backoff/rate-limit/cache; tool độc
   lập chạy song song.
6. **Dùng đúng idiom LangGraph**: checkpointer-backed thread cho memory/resume; mỗi sub-agent là
   agent ReAct (tự chain tool).
7. **Observability & lỗi là mối quan tâm xuyên suốt**: logging có cấu trúc + cây exception
   domain + tracing, wiring một lần.

### 4.2 Mô hình swarm (thay đổi cốt lõi — theo D2)

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
     │ ReAct + Sui RPC │ │ ReAct +      │  │ ReAct + Tavily   │
     │ tools           │ │ CoinGecko/GT │  │                  │
     └─────────────────┘ └──────────────┘  └──────────────────┘
```

- **Supervisor**: nhận yêu cầu, định tuyến tới một hoặc nhiều sub-agent, tổng hợp kết quả, sinh
  câu trả lời cuối. Có thể dùng prebuilt **`langgraph-supervisor`** (ít code) hoặc node tự viết.
- **Sub-agent là agent ReAct**: mỗi agent có prompt riêng + một **tập tool con** + có thể dùng
  model riêng. Vì là ReAct, **chain tool phụ thuộc xảy ra tự nhiên trong nội bộ sub-agent** —
  giải quyết luôn vấn đề 🔴 ở [§3.2](#32-kiến-trúc-agent).
- **Handoff**: hỗ trợ chuyển quyền giữa các agent (kiểu swarm) khi một agent nhận ra việc thuộc
  về agent khác. Trạng thái "agent đang hoạt động" được lưu trong state.

**Các sub-agent v1:**

| Sub-agent | Vai trò | Tập tool |
|---|---|---|
| **Sui On-chain** *(lõi)* | Truy vấn **& thao tác** Sui: số dư, object, metadata, tx block, staking, DeFi, **ký/gửi tx** | `tools/sui/*` → **REST API NestJS** *(bật ở Phase 8)* |
| **Market-data** | Giá/market cap/volume, top movers, chart/OHLC, pool DEX (gồm cả mạng Sui trên GeckoTerminal) | `tools/market/coingecko/*`, `tools/market/geckoterminal/*` |
| **Research/Web** | Tin tức, tài liệu, bối cảnh | `tools/web/search.py` (Tavily) |

> **Trạng thái v1:** chỉ **Market-data + Research** hoạt động (NestJS chưa dựng). Sub-agent
> **Sui** được scaffold sẵn và bật ở **Phase 8**.

> **Lưu ý đồng vận**: GeckoTerminal đã hỗ trợ mạng **Sui** cho dữ liệu DEX on-chain → market
> agent bổ trợ tốt cho Sui agent (giá pool/thanh khoản trên Sui).

> **Ranh giới Sui (D5, D6)**: sub-agent Sui **không gọi Sui RPC trực tiếp** — tool của nó gọi
> **REST API của service NestJS** (nơi giữ ví/khóa riêng của agent, ký & gửi tx, nói chuyện với
> Sui RPC). Phía Python **không giữ key**. **Phạm vi: full (đọc + ghi)** — agent được tự do thao
> tác; phần chặn/guardrail do một **repo policy contract riêng** đảm nhiệm, **KHÔNG gate ở agent
> này**. Đổi lại, phía Python phải **log/trace rõ mọi hành động ghi** để audit được.

### 4.3 Sơ đồ thành phần tổng thể

```text
        ┌──────────────────────── interfaces ───────────────────────┐
        │   CLI (Typer + Rich, streaming)     API (FastAPI + Docker) │
        └───────────────┬───────────────────────────┬───────────────┘
                        │                            │
        ┌───────────────▼────────────────────────────▼──────────────┐
        │                    agent core (SWARM)                       │
        │   supervisor · agents/{sui_onchain, market, research}       │
        │   state · graph(builder) · handoffs · prompts/              │
        └───────┬───────────────────┬───────────────────────┬────────┘
                │                   │                       │
      ┌─────────▼──────┐   ┌────────▼─────────┐   ┌─────────▼─────────┐
      │   llm/factory  │   │   tools/ (thin   │   │   memory/         │
      │ (đa provider)  │   │   @tool adapters)│   │   checkpointer    │
      └────────────────┘   └────────┬─────────┘   └───────────────────┘
                                    │
                      ┌─────────────▼──────────────┐
                      │   services (logic domain)   │
                      │  sui · coingecko · gecko-   │
                      │  terminal · web · system    │
                      └─────────────┬──────────────┘
                                    │
        ┌───────────────────────────▼───────────────────────────────┐
        │                     infrastructure                          │
        │  http client (retry/backoff/ratelimit/cache) · observability│
        │  (langfuse + logging) · settings(config) · persistence      │
        └─────────────────────────────────────────────────────────────┘
```

> **Ranh giới quan trọng (D5)**: domain *Sui* trong sơ đồ trên KHÔNG gọi Sui RPC trực tiếp từ
> Python. Toàn bộ tương tác Sui nằm ở một **service NestJS riêng (ngoài repo này)**; `tools/sui/*`
> chỉ là **HTTP client gọi REST API** của service đó — giống hệt cách gọi CoinGecko. Việc giữ
> key / ký giao dịch / nói chuyện với Sui RPC thuộc về NestJS.
>
> ```text
> tools/sui  ──HTTP/REST──►  Service NestJS (repo khác)  ──Sui RPC──►  Sui blockchain
> ```

---

## 5. Cấu trúc thư mục mục tiêu

```text
SuiSwarm-Agent/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                  # lint + type-check + test + coverage khi mở PR
│   │   └── docker.yml              # build & push image
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE.md
├── docs/                           # TIẾNG VIỆT (D4)
│   ├── index.md
│   ├── REFACTORING_PLAN.md         # ← tài liệu này
│   ├── kien-truc/
│   │   ├── tong-quan.md
│   │   └── adr/                    # Architecture Decision Records
│   │       ├── 0001-ghi-nhan-quyet-dinh-kien-truc.md
│   │       ├── 0002-kien-truc-phan-lop.md
│   │       ├── 0003-swarm-supervisor-subagent.md
│   │       ├── 0004-sui-qua-service-nestjs.md
│   │       └── 0005-quyen-agent-va-policy-contract.md
│   └── huong-dan/
│       ├── cau-hinh.md             # tham chiếu đầy đủ env/settings
│       ├── them-tool.md
│       ├── them-sub-agent.md
│       ├── them-llm-provider.md
│       ├── kiem-thu.md
│       └── trien-khai.md           # CLI + Docker + API
├── scripts/                        # script tiện ích dev (smoke-test, seed, ...)
├── src/suiswarm_agent/
│   ├── __init__.py                 # __version__ single-source (importlib.metadata)
│   ├── __main__.py                 # python -m suiswarm_agent
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py             # MỘT Settings có type (lồng: llm, sui, coingecko,
│   │                               #   geckoterminal, tavily, langfuse, http, agent, server)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── constants.py            # gom giới hạn/budget
│   │   ├── exceptions.py           # cây exception domain
│   │   └── logging.py              # cấu hình logging có cấu trúc
│   ├── llm/
│   │   ├── __init__.py
│   │   └── factory.py              # factory chat-model đa provider, override theo vai
│   ├── agent/                      # SWARM (đổi tên từ graph/)
│   │   ├── __init__.py             # export `graph` đã compile
│   │   ├── state.py                # state swarm (messages, active_agent, scratch)
│   │   ├── graph.py                # build swarm: supervisor + worker + checkpointer
│   │   ├── supervisor.py           # node điều phối/định tuyến
│   │   ├── handoffs.py             # handoff tool giữa các agent
│   │   ├── agents/                 # các thành viên của swarm
│   │   │   ├── __init__.py
│   │   │   ├── base.py             # factory tạo ReAct sub-agent (prompt, toolset, model)
│   │   │   ├── sui_onchain.py      # sub-agent LÕI
│   │   │   ├── market.py           # sub-agent thị trường
│   │   │   └── research.py         # sub-agent web/nghiên cứu
│   │   └── prompts/
│   │       ├── __init__.py
│   │       ├── supervisor.py
│   │       ├── sui_onchain.py
│   │       ├── market.py
│   │       └── research.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── base.py                 # ToolSpec, namespacing, đăng ký có điều kiện
│   │   ├── registry.py             # chỉ expose tool đang khả dụng (theo key đã cấu hình)
│   │   ├── sui/                    # DOMAIN LÕI (D1) — client tới NestJS (D5)
│   │   │   ├── client.py           # SuiServiceClient (HTTP async → REST API NestJS)
│   │   │   ├── service.py          # hàm domain map sang endpoint NestJS
│   │   │   ├── models.py           # pydantic DTO mirror theo NestJS (từ OpenAPI nếu có)
│   │   │   └── tools.py            # @tool mỏng
│   │   ├── market/
│   │   │   ├── coingecko/
│   │   │   │   ├── client.py
│   │   │   │   ├── service.py
│   │   │   │   ├── models.py
│   │   │   │   └── tools.py
│   │   │   └── geckoterminal/
│   │   │       ├── client.py
│   │   │       ├── service.py
│   │   │       ├── models.py
│   │   │       └── tools.py
│   │   ├── web/
│   │   │   └── search.py           # tavily (khởi tạo lazy, có điều kiện)
│   │   └── system/
│   │       └── builtin.py
│   ├── infra/
│   │   ├── __init__.py
│   │   ├── http/
│   │   │   └── client.py           # httpx async dùng chung: retry/backoff/ratelimit/cache
│   │   └── observability/
│   │       ├── __init__.py
│   │       └── langfuse.py
│   ├── memory/
│   │   ├── __init__.py
│   │   └── checkpoint.py           # checkpointer LangGraph (sqlite dev/CLI · postgres API)
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── plan.py
│   │   └── tools.py
│   └── interfaces/
│       ├── __init__.py
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── app.py              # Typer (streaming, cờ --model/--temperature/--thread-id)
│       │   └── render.py           # helper render Rich
│       └── api/                    # TRONG PHẠM VI (D3)
│           ├── __init__.py
│           ├── app.py              # FastAPI: /chat, /chat/stream, /healthz
│           ├── routes.py
│           ├── schemas.py          # DTO request/response
│           └── deps.py             # dependency injection
├── tests/
│   ├── conftest.py
│   ├── fixtures/                   # phản hồi API ghi sẵn / cassette
│   ├── unit/                       # service, client (mock http), node (mock llm)
│   ├── integration/                # graph end-to-end với fake
│   └── e2e/                        # opt-in, API thật, mặc định skip trong CI
├── .env.example                    # đầy đủ, nhóm theo concern, có chú thích
├── .python-version
├── .pre-commit-config.yaml
├── .dockerignore
├── .gitignore
├── Dockerfile
├── docker-compose.yml              # app + postgres (+ langfuse tùy chọn) cho local
├── Makefile                        # make install/lint/type/test/run/fmt/up
├── pyproject.toml                  # nguồn dependency duy nhất + cfg ruff/mypy/pytest/coverage
├── uv.lock                         # cài tái lập, pin version
├── LICENSE
├── CHANGELOG.md
├── CONTRIBUTING.md
└── README.md                       # mục đích + quickstart + link vào docs/
```

> **`requirements.txt` bị bỏ**, thay bằng `pyproject.toml` (deps) + lock file. Nếu một số môi
> trường deploy vẫn cần `requirements.txt` phẳng, hãy **sinh ra từ lock file** để không bị lệch.

---

## 6. Tiêu chuẩn xuyên suốt

### 6.1 Cấu hình

- Một `Settings` (pydantic-settings) với **các model lồng theo concern**: `llm`, `sui_service`,
  `coingecko`, `geckoterminal`, `tavily`, `langfuse`, `http`, `agent`, `server`. Dùng
  `env_nested_delimiter="__"` (vd `LLM__PROVIDER`, `SUI_SERVICE__BASE_URL`, `HTTP__TIMEOUT`).
- **Không module nào đọc `os.environ` trực tiếp** — tất cả qua `get_settings()`.
- `load_dotenv()` gọi **một lần** ở entrypoint (CLI/API), không gọi mỗi lần.
- Lệnh `suiswarm config check` (hoặc banner lúc khởi động) validate key và in ra năng lực nào
  đang bật/tắt (kết nối được service NestJS Sui không, có Tavily/CoinGecko không, ...).

### 6.2 Trừu tượng hóa LLM provider

- `llm/factory.py: get_chat_model(role=..., **overrides)` trả `BaseChatModel` theo
  `settings.llm.provider`; model/temperature theo vai lấy từ config.
- OpenAI là mặc định; cấu trúc sao cho thêm Anthropic/Azure/Ollama là cộng thêm (không sửa call-site).

### 6.3 HTTP & khả năng chịu lỗi

- `infra/http/client.py`: một `httpx.AsyncClient` dùng chung (connection pool) với **retry +
  exponential backoff** (vd `tenacity`), **rate limiting**, timeout cấu hình được, và **cache
  TTL ngắn tùy chọn** cho các lệnh đọc idempotent (Sui service, market). Mọi service client dùng nó.

### 6.4 Lỗi & logging

- `core/exceptions.py`: cây — `SuiSwarmError` → `ConfigError`, `ToolError` (`ToolNotFound`,
  `ToolExecutionError`, `UpstreamAPIError`, `RateLimitedError`), `LLMError`, `SuiServiceError` (lỗi từ service NestJS).
- `core/logging.py`: logging có cấu trúc (JSON ở prod, đẹp ở dev) kèm correlation id theo
  session/request. Thay `except Exception` câm bằng catch có type + log context. Thông điệp lỗi
  cho user được làm sạch (không lộ payload upstream thô).

### 6.5 Observability

- Giữ Langfuse, cấu hình từ Settings có type, wiring một lần. Thêm span đo thời gian quanh
  node/sub-agent/tool. Có health/readiness cho API.

### 6.6 Chiến lược kiểm thử

- **pytest** + `pytest-asyncio` + coverage. Bố cục: `unit/` (service/client mock HTTP bằng
  `respx`/fixture ghi sẵn; node mock LLM), `integration/` (graph compile với model fake +
  tool fake), `e2e/` (API thật, marker opt-in, mặc định skip trong CI).
- Mục tiêu: phủ có ý nghĩa cho service, client, routing, logic node. Bổ sung test cho swarm
  (định tuyến supervisor, handoff) và Sui client (mock REST API của service NestJS).

### 6.7 CI/CD & cổng chất lượng

- `.github/workflows/ci.yml`: matrix (3.11–3.13) → `ruff check` + `ruff format --check` +
  `mypy` + `pytest --cov` (fail nếu dưới ngưỡng). `docker.yml` build image.
- `pyproject.toml` cấu hình **ruff** (lint+format), **mypy** (gần strict), **pytest**,
  **coverage**. Thêm `.pre-commit-config.yaml`, thêm `py.typed`.

### 6.8 Đóng gói & triển khai

- Một nguồn dependency trong `pyproject.toml` + nhóm `[project.optional-dependencies] dev`;
  **xóa `requirements.txt`**; thêm **lock file** (khuyến nghị `uv`). Khai báo các dep trực tiếp
  đang thiếu (`openai`, `pydantic`, `typing_extensions`).
- Single-source `__version__` (vd `importlib.metadata.version`).
- **Docker (D3)**: `Dockerfile` đa stage (build → runtime gọn), `docker-compose.yml` (app +
  postgres cho checkpointer + langfuse tùy chọn). Thêm `Makefile`, `LICENSE`, `CHANGELOG.md`,
  `CONTRIBUTING.md`, `.python-version`.

### 6.9 Bảo mật

- **Key custody & guardrail nằm NGOÀI repo này (D5, D6).** Service NestJS giữ ví/khóa riêng của
  agent và ký tx; một repo **policy contract** riêng thực thi giới hạn. Theo chỉ đạo, agent được
  **full quyền (đọc + ghi)**, KHÔNG gate ở phía Python. Đổi lại, repo này phải **log/trace mọi
  hành động ghi** (tool nào, input gì, kết quả) để audit được khi cần.
- URL-encode mọi path do user nhập (Sui address, contract address, network).
- Không log secret; làm sạch lỗi trước khi trả cho user; giới hạn kích thước input.

---

## 7. Lộ trình triển khai theo phase

Mỗi phase ship độc lập, **giữ CLI luôn chạy được**. Công sức: **S** ≈ <½ ngày, **M** ≈ 1–2
ngày, **L** ≈ 3–5 ngày (một kỹ sư, ước lượng thô).

### Phase 0 — Dựng hàng rào an toàn trước *(M)*
*Mục tiêu: an toàn để thay đổi, trước khi thay đổi.*
- Thêm cấu hình ruff + mypy + pytest + coverage vào `pyproject.toml`; thêm `.pre-commit-config.yaml`.
- Chuyển test sang **pytest**; thêm **mock HTTP** (`respx`) + **LLM fake**; thêm smoke test cho graph.
- Thêm `.github/workflows/ci.yml` (lint + type + test). Thêm `LICENSE`, `.python-version`.
- **Tiêu chí xong:** CI xanh trên `main`; `make lint type test` chạy pass local.

### Phase 1 — Hợp nhất cấu hình & đóng gói *(M)*
*Mục tiêu: một bề mặt config, một nguồn dependency.*
- `Settings` lồng (llm/sui/coingecko/geckoterminal/tavily/langfuse/http/agent/server). Đưa
  Langfuse + Tavily qua nó; bỏ `os.getenv`/`load_dotenv` rải rác.
- Một nguồn dependency trong `pyproject.toml` (khai báo `openai`, `pydantic`,
  `typing_extensions`), thêm extra `dev`, sinh lock file, xóa `requirements.txt`.
- Single-source `__version__`. Viết lại `.env.example` (nhóm + chú thích, gồm cả `SUI__*`).
- **Tiêu chí xong:** `suiswarm config check` báo năng lực đang bật; cài lại từ lock tái lập
  được; test vẫn xanh.

### Phase 2 — Tầng hạ tầng (HTTP + logging + lỗi) *(M)*
*Mục tiêu: I/O chịu lỗi + chẩn đoán thật.*
- Dựng `infra/http/client.py` (async, retry/backoff, rate limit, timeout, cache tùy chọn).
- Thêm `core/logging.py` + `core/exceptions.py`; thay `except` rộng bằng xử lý có type + log.
- **Tiêu chí xong:** test mô phỏng 429/5xx retry thành công; log hiện span node/tool; không lộ
  text upstream thô cho user.

### Phase 3 — Tái cấu trúc tầng tool (market + web) + chuẩn bị seam Sui *(L)*
*Mục tiêu: xóa god module; tool mỏng trên service; chuẩn bị sẵn chỗ cắm cho Sui.*
- Tách `tools/coingecko.py` → `tools/market/coingecko/{client,service,models,tools}.py` và
  `tools/market/geckoterminal/{...}.py`, tất cả dùng HTTP client async chung.
- **Chuẩn bị seam `tools/sui/`** (CHƯA hiện thực hóa — NestJS chưa dựng): chỉ tạo interface
  `SuiServiceClient` + config `SUI_SERVICE__*` (base URL + API key header) làm chỗ cắm sẵn. Tool
  Sui live + bật sub-agent Sui để ở **Phase 8** khi service NestJS sẵn sàng.
- `tools/web/search.py` lazy + có điều kiện. Chuyển builtin sang `tools/system/`.
- `tools/base.py` (namespacing, **đăng ký có điều kiện** theo key) + registry chỉ expose tool
  khả dụng; **nhóm tool** để supervisor/sub-agent thấy bản tóm tắt gọn thay vì 28 schema đầy đủ.
- **Tiêu chí xong:** hành vi tool (với user) không đổi; unit test phủ service (mock HTTP);
  kích thước prompt giảm rõ; thiếu key → tool đơn giản là vắng mặt.

### Phase 4 — Trừu tượng hóa LLM provider *(S–M)*
- `llm/factory.py` (đa provider, model/temp theo vai lấy từ config). Đưa hằng temperature ra
  khỏi code vào settings (xử lý gọn cái diff `llm.py` đang treo).
- **Tiêu chí xong:** đổi `LLM__PROVIDER`/model qua env không cần sửa code; các node lấy model
  từ factory.

### Phase 5 — Lõi swarm đa agent *(L)*  ⟵ tác động sản phẩm lớn nhất (D2)
- Tổ chức lại `graph/ → agent/` với `supervisor.py`, `agents/{base,sui_onchain,market,research}`,
  `handoffs.py`, `prompts/`.
- Mỗi sub-agent là **agent ReAct** (tự chain tool của mình). **Supervisor** định tuyến tới một/
  nhiều sub-agent rồi tổng hợp (dùng `langgraph-supervisor` hoặc tự viết — xem [§8](#8-chiến-lược-migration--các-quyết-định-còn-lại)).
- **Trước mắt v1 chỉ bật Market-data + Research** (bằng tool hiện có); sub-agent Sui scaffold
  sẵn nhưng **kích hoạt ở Phase 8** khi NestJS sẵn sàng.
- Thực thi tool **async + song song** trong nội bộ mỗi sub-agent.
- Wiring **checkpointer** (`memory/checkpoint.py`) + `thread_id`; bỏ nối message thủ công ở CLI.
  Thêm **tóm tắt** context/kết quả thay vì nhồi repr thô.
- **Tiêu chí xong:** "tìm coin id của X rồi cho chi tiết" chạy trong một lượt; truy vấn độc lập
  chạy song song; hội thoại resume xuyên lần chạy qua thread id; supervisor định tuyến đúng
  domain (market vs web; Sui bật ở Phase 8).

### Phase 6 — Giao diện & UX: CLI + **API + Docker** *(M–L)* (D3)
- CLI dưới `interfaces/cli/` với **streaming**, cờ `--model`/`--temperature`/`--thread-id`,
  render Rich (bảng cho dữ liệu thị trường / số dư Sui). Thêm `__main__.py`.
- **API (D3)**: `interfaces/api/` FastAPI — `/chat`, `/chat/stream` (SSE), `/healthz`; DTO
  request/response; DI; checkpointer Postgres cho phiên đa người dùng.
- **Docker (D3)**: `Dockerfile` đa stage + `docker-compose.yml` (app + postgres + langfuse tùy
  chọn) + `.dockerignore` + workflow build image.
- **Tiêu chí xong:** token stream ở terminal; API phục vụ một lượt chat + health check; `docker
  compose up` chạy được full stack local.

### Phase 7 — Tài liệu (tiếng Việt) & hoàn thiện định danh *(M–L)* (D4)
- Viết đầy đủ `docs/` (tiếng Việt): tổng quan kiến trúc, ADR (gồm swarm & Sui-qua-NestJS),
  tham chiếu cấu hình, hướng dẫn thêm tool/sub-agent/provider, hướng dẫn triển khai.
- Viết lại README quanh mục đích thật (Sui-first swarm); thêm `CONTRIBUTING.md`, `CHANGELOG.md`.
- **Tiêu chí xong:** tên khớp năng lực; người mới thêm được tool/sub-agent theo hướng dẫn; ADR
  ghi lại các quyết định D1–D6.

### Phase 8 — Tích hợp Sui qua service NestJS *(M–L, phụ thuộc NestJS sẵn sàng)* (D5, D6)
*Mục tiêu: hiện thực hóa domain lõi Sui khi service NestJS đã có.*
- Hiện thực `SuiServiceClient` theo contract thật (ưu tiên sinh/mirror model từ OpenAPI của
  NestJS); viết `service` + `@tool` cho cả thao tác **đọc và ghi** (full quyền — D6).
- **Bật sub-agent Sui** trong swarm; supervisor định tuyến truy vấn/thao tác on-chain sang đây.
- **Log/trace mọi hành động ghi** để audit (guardrail thực thi bởi repo *policy contract* riêng).
- **Tiêu chí xong:** hỏi on-chain Sui (số dư/đối tượng/tx) trả lời được qua agent; hành động ghi
  chạy qua NestJS và được trace đầy đủ; thiếu `SUI_SERVICE__*` → sub-agent Sui tự ẩn (degrade mượt).

---

## 8. Chiến lược migration & các quyết định còn lại

### 8.1 Cách migration không gãy

- **Chạy song song cấu trúc cũ/mới**: dựng lớp `infra` + `config` + `services` mới trước, để
  module cũ tạm import vào, rồi mới cắt dần `@tool` sang service.
- **Giữ entry point `suiswarm`** xuyên suốt; chỉ đổi nội bộ. Đổi tên `graph/ → agent/` làm ở
  Phase 5 kèm shim tạm export lại để không vỡ import.
- **Mỗi phase một PR (hoặc vài PR nhỏ)**, CI xanh trước khi merge; cập nhật `CHANGELOG.md`.

### 8.2 Quyết định còn lại (đã có đề xuất mặc định — bạn có thể chỉnh)

| # | Quyết định | Mặc định đề xuất |
|---|---|---|
| Q5 | **Auth tới service NestJS** | ✅ **Đã chốt: API key ở header**, qua `SUI_SERVICE__BASE_URL` / `SUI_SERVICE__API_KEY`. |
| Q6 | **Quyền agent với Sui** | ✅ **Đã chốt: full (đọc + ghi), không gate ở Python.** Guardrail do repo *policy contract* riêng lo; agent dùng key riêng (NestJS giữ). |
| Q7 | **Nguồn contract** | Ưu tiên **OpenAPI/Swagger** từ NestJS để sinh/mirror model. *NestJS chưa dựng → chốt khi service sẵn sàng (Phase 8).* |
| Q8 | **Thư viện swarm** | Bắt đầu với prebuilt **`langgraph-supervisor`** (ít code); fallback tự viết supervisor nếu cần kiểm soát sâu. |
| Q9 | **Persistence** | **SQLite** cho dev/CLI; **Postgres** (qua config) cho API/Docker. |
| Q10 | **LLM provider** | Xây abstraction nhưng **mặc định OpenAI**; thêm Claude/khác là cộng thêm. |
| Q11 | **Tooling** | Chuẩn hóa **`uv` + ruff + mypy + pytest**, target Python **3.11–3.13**. |
| Q12 | **Tương thích ngược** | Tự do thay đổi nội bộ (v0.x); ghi lại ở `CHANGELOG.md`. |

> Q5/Q6 đã chốt. Việc còn lại chủ yếu chờ **service NestJS được dựng** (Q7 — contract) — khi đó
> mới hiện thực hóa `tools/sui/` ở **Phase 8**. Trước đó, agent v1 chạy bằng tool market +
> research. Q8–Q12 (provider, persistence, tooling...) dùng mặc định, bạn có thể chỉnh bất cứ lúc nào.

---

## 9. Phụ lục

### 9.1 Quick wins (an toàn, giá trị cao, rủi ro thấp — làm ngay được)
- Khai báo 3 dep trực tiếp đang thiếu (`openai`, `pydantic`, `typing_extensions`).
- Thêm `LICENSE`, `.python-version`, config ruff/mypy/pytest, `Makefile`.
- Đưa temperature/limit của planner-responder vào `Settings`/`constants.py` (xử lý gọn diff
  `llm.py` đang treo).
- Làm `tools/search.py` lazy (bỏ `TavilySearch()` / `load_dotenv()` lúc import).
- URL-encode path do user nhập trong tool thị trường (và sau này là Sui address).
- Gọi `load_dotenv()` đúng một lần ở entrypoint.

### 9.2 Quy ước (đề xuất)
- **Style/lint/format:** ruff. **Type:** mypy (không cho hàm thiếu type trong `src/`).
- **Commit:** Conventional Commits. **Nhánh:** feature branch ngắn → PR → CI xanh.
- **Docs:** Markdown trong `docs/` (tiếng Việt); quyết định lớn ghi thành ADR.
- **Async:** code I/O-bound viết `async`; tool expose async khi client bên dưới là async.

### 9.3 Definition of Done (mỗi thay đổi)
- Lint + format + type-check + test pass trong CI; logic mới có test.
- Không `os.environ`/`load_dotenv` ngoài config/entrypoint; không `except Exception` câm thiếu
  log + xử lý có type.
- Thay đổi hành vi public phản ánh vào docs + `CHANGELOG.md`.

---

*Hết kế hoạch. Phản hồi và lựa chọn cho [§8.2](#82-quyết-định-còn-lại-đã-có-đề-xuất-mặc-định--bạn-có-thể-chỉnh)
sẽ được gộp vào bản cập nhật trước khi bắt đầu code.*
