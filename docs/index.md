# Tài liệu SuiSwarm Agent

> Ngôn ngữ: **Tiếng Việt** (D4) · Thuật ngữ kỹ thuật giữ nguyên tiếng Anh khi đó là chuẩn ngành.

**SuiSwarm Agent** là một **"đàn" (swarm) các AI agent chuyên biệt lấy Sui blockchain làm trọng
tâm**, do một **supervisor** điều phối, xây trên **LangGraph**. Một supervisor định tuyến yêu cầu
tới nhiều **sub-agent ReAct** (mỗi sub-agent tự chain được tập tool của mình), rồi tổng hợp câu
trả lời cuối. Dự án phục vụ qua **cả CLI và REST API**, đóng gói **Docker** (D3).

Mọi tương tác Sui (RPC, giữ key, ký giao dịch) nằm ở một **service NestJS riêng (ngoài repo
này)**; phía Python chỉ **gọi qua REST API** và **không giữ key** (D5). Agent có **full quyền
đọc + ghi** trên Sui, **không gate ở Python** — guardrail do một **repo policy contract riêng**
đảm nhiệm (D6).

> **Phạm vi trước mắt (v1):** service NestJS *chưa được dựng*, nên agent v1 chạy bằng sub-agent
> **Market-data (CoinGecko/GeckoTerminal)** + **Research/Web (Tavily)**. Sub-agent **Sui** được
> chuẩn bị sẵn chỗ cắm và tích hợp đầy đủ ở **Phase 8** khi NestJS sẵn sàng.

---

## Các quyết định nền tảng (D1–D6)

| # | Quyết định | Lựa chọn đã chốt |
|---|---|---|
| D1 | Định hướng sản phẩm | **Sui-first on-chain** (Sui là domain lõi; market data là phụ trợ) |
| D2 | Mô hình agent | **Multi-agent swarm**: supervisor + sub-agent ReAct |
| D3 | Giao diện / triển khai | **CLI + REST API + Docker** |
| D4 | Ngôn ngữ tài liệu | **Tiếng Việt** |
| D5 | Triển khai Sui | **Service NestJS riêng**; Python gọi REST, không RPC trực tiếp, không giữ key |
| D6 | Quyền agent với Sui | **Full (đọc + ghi), không gate ở Python**; guardrail do repo policy contract riêng |

---

## Bản đồ tài liệu

### Kế hoạch & nguồn chân lý

- [Kế hoạch Refactor & Kiến trúc (REFACTORING_PLAN.md)](REFACTORING_PLAN.md) — nguồn chân lý duy
  nhất: hiện trạng, danh mục vấn đề, kiến trúc mục tiêu, cấu trúc thư mục, lộ trình theo phase,
  chiến lược migration, và các quyết định D1–D6.

### Kiến trúc

- [Tổng quan kiến trúc](kien-truc/tong-quan.md) — nguyên tắc phân lớp, mô hình swarm, ranh giới
  Sui qua NestJS, sơ đồ luồng request, và bảng trách nhiệm từng package trong `src/`.
- [Architecture Decision Records (ADR)](kien-truc/adr/) — ghi lại các quyết định kiến trúc lớn:
  - `0001-ghi-nhan-quyet-dinh-kien-truc.md`
  - `0002-kien-truc-phan-lop.md`
  - `0003-swarm-supervisor-subagent.md`
  - `0004-sui-qua-service-nestjs.md`
  - `0005-quyen-agent-va-policy-contract.md`

### Hướng dẫn (huong-dan/)

- [Cấu hình](huong-dan/cau-hinh.md) — tham chiếu đầy đủ env/Settings (secret theo tên quy ước +
  cấu hình có cấu trúc theo dấu `__`).
- [Thêm tool](huong-dan/them-tool.md) — quy trình thêm một tool mới (client → service → models →
  `@tool` wrapper, đăng ký có điều kiện trong registry).
- [Thêm sub-agent](huong-dan/them-sub-agent.md) — thêm một thành viên ReAct mới vào swarm và
  wiring vào supervisor.
- [Thêm LLM provider](huong-dan/them-llm-provider.md) — mở rộng `llm/factory.py` cho provider
  mới mà không sửa call-site.
- [Kiểm thử](huong-dan/kiem-thu.md) — chạy `make test` / `pytest`; bố cục `tests/unit` +
  `tests/integration`; mock HTTP bằng `respx`, không gọi LLM thật.
- [Triển khai](huong-dan/trien-khai.md) — chạy CLI, REST API (FastAPI/uvicorn), và Docker.

---

## Stack chính

Python 3.11–3.13 (dev 3.13) · LangGraph 1.x · langgraph-supervisor · langgraph-checkpoint-sqlite
· LangChain 1.x (core/openai) · langchain-tavily · Langfuse 4.x · FastAPI + uvicorn · httpx +
tenacity · pydantic 2.x + pydantic-settings · Typer + Rich · OpenAI 2.x.

> Lưu ý: tài liệu mô tả **kiến trúc đích đầy đủ**. Tính năng nào còn ở giai đoạn sau (đặc biệt là
> tích hợp Sui ở Phase 8) được ghi rõ trong từng trang. Mọi nội dung bám sát
> [REFACTORING_PLAN.md](REFACTORING_PLAN.md).
