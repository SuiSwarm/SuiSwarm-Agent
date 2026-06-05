# ADR 0003 — Swarm đa agent: supervisor + sub-agent ReAct

## Trạng thái

Accepted (Đã chấp thuận) · Ngày: 2026-06-03 · Hiện thực hóa quyết định D2

## Bối cảnh

Mô hình agent ban đầu chạy **một lượt**: `plan → execute_tools → respond`. Planner dùng LLM
`with_structured_output` để chọn toàn bộ 1–5 bước tool **trước khi chạy bất kỳ tool nào**, rồi
executor chạy "mù" theo danh sách đó trong một vòng `for` đồng bộ.

Cách này có hai khiếm khuyết cốt lõi:

1. **Không chain được tool phụ thuộc.** Planner phải quyết hết trước, nên không làm được chuỗi
   "search → dùng ID trả về → lấy chi tiết" — đúng kịch bản mà công cụ kiểu `coingecko_search`
   sinh ra để phục vụ. Không có vòng lặp quay lại planner.
2. **Thực thi tuần tự, đồng bộ.** Các bước độc lập (ví dụ "giá BTC" và "trending pools") chạy
   nối tiếp bằng lời gọi HTTP blocking, không async, không song song.

Đồng thời, định danh sản phẩm "SuiSwarm" ngụ ý một *swarm* đa agent, nhưng mô hình một-agent-một-
lượt không phản ánh điều đó. Dự án cần một mô hình điều phối vừa giải quyết hai khiếm khuyết trên,
vừa khớp định hướng đa agent (D2) và Sui-first (D1, với domain Sui là một sub-agent lõi).

## Quyết định

Thay mô hình *plan-tất-cả-rồi-chạy* bằng **swarm đa agent điều phối bởi một supervisor** (D2):

- **Supervisor** — `agent/supervisor.py` dùng `langgraph_supervisor.create_supervisor`. Supervisor
  nhận yêu cầu, **định tuyến tới một hoặc nhiều sub-agent**, tổng hợp kết quả và sinh câu trả lời
  cuối. CLI stream token của supervisor.
- **Sub-agent là agent ReAct** — `agent/agents/{market,research,sui_onchain}.py` dùng
  `build_worker_agent` (trên nền `create_react_agent`). Mỗi sub-agent có prompt riêng
  (`SUPERVISOR_PROMPT`, `MARKET_PROMPT`, `RESEARCH_PROMPT`, `SUI_ONCHAIN_PROMPT` trong
  `agent/prompts.py`) và một **tập tool con** lấy từ registry.
- **Chain tool phụ thuộc xảy ra tự nhiên bên trong sub-agent.** Vì là vòng lặp ReAct, sub-agent
  tự quan sát kết quả tool và quyết bước tiếp theo — giải quyết khiếm khuyết "search → chi tiết"
  mà không cần planner toàn cục.
- **Song song & async.** Tool I/O chạy trên `AsyncHttpClient` chung (httpx async, retry/backoff,
  rate-limit, cache); các nhánh độc lập có thể chạy song song thay vì nối tiếp blocking.
- **Graph & state** — `agent/state.py` (`AgentState = MessagesState`), `agent/graph.py`
  (`build_graph(checkpointer, settings)` và `make_graph()` factory). Graph **tự bật sub-agent Sui
  khi service được cấu hình**; mặc định `enabled_agents = ['market', 'research']`.
- **Thư viện**: bắt đầu với prebuilt `langgraph-supervisor` (0.0.31) để ít code; có thể fallback
  sang supervisor tự viết nếu cần kiểm soát sâu hơn.

## Hệ quả

**Tích cực:**

- "Tìm coin id của X rồi lấy chi tiết" chạy gọn trong nội bộ một sub-agent (chain tool phụ thuộc);
  các truy vấn độc lập có thể chạy song song.
- Định danh khớp thực tế: supervisor + nhiều sub-agent chuyên biệt đúng nghĩa "swarm".
- Mở rộng dễ: thêm một sub-agent mới = thêm một file `agent/agents/*.py` + prompt + tập tool, rồi
  khai báo trong `enabled_agents`.
- Domain Sui cắm vào tự nhiên như sub-agent lõi, bật khi service sẵn sàng (xem ADR 0004).

**Tiêu cực / đánh đổi:**

- Nhiều lượt LLM hơn (supervisor định tuyến + vòng ReAct của sub-agent) so với một-lượt cũ → có
  thể tốn token/độ trễ hơn cho truy vấn đơn giản.
- Cần đặt `AGENT__RECURSION_LIMIT` và prompt định tuyến hợp lý để tránh vòng lặp/handoff không
  hội tụ; routing của supervisor cần được test riêng.

**Trung tính:**

- Lộ trình theo phase: v1 chỉ bật **market + research** (NestJS chưa dựng); sub-agent **Sui** được
  scaffold sẵn và kích hoạt đầy đủ ở **Phase 8** khi service NestJS sẵn sàng.
- Checkpointer (`memory/checkpoint.py`) cấp memory/resume theo thread thay cho việc nối message
  thủ công ở CLI trước đây.
