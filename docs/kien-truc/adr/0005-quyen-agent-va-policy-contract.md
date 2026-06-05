# ADR 0005 — Quyền agent với Sui và policy contract ngoài

## Trạng thái

Accepted (Đã chấp thuận) · Ngày: 2026-06-03 · Hiện thực hóa quyết định D6

## Bối cảnh

Theo ADR 0004 (D5), mọi tương tác Sui đi qua service NestJS, nơi giữ ví/khóa riêng của agent và
ký giao dịch. Câu hỏi còn lại là: **agent được phép làm gì** với Sui (chỉ đọc, hay cả ghi/ký tx),
và **chốt chặn an toàn (guardrail)** đặt ở đâu?

Có thể đặt guardrail ngay trong repo agent Python: ví dụ gate các hành động ghi (chặn, yêu cầu
xác nhận, áp hạn mức) trước khi gọi service. Tuy nhiên, nếu logic chính sách nằm rải trong agent
Python, nó dễ bị bỏ qua khi có nhiều giao diện (CLI, API), khó kiểm toán nhất quán, và lẫn lộn
mối quan tâm "điều phối/gọi LLM" với "thực thi chính sách on-chain". Trong khi đó, dự án đã có chủ
trương tách phần on-chain ra service riêng, và phần ràng buộc chính sách hợp lý hơn khi nằm gần
nơi nắm key và ký tx — hoặc ở một thành phần chính sách chuyên trách.

## Quyết định

Agent có **full quyền đọc + ghi** với Sui, và **KHÔNG gate ở phía Python** (D6):

- **Phạm vi: full (đọc + ghi).** Agent được tự do thao tác Sui (bao gồm hành động ghi/ký tx, thực
  hiện qua service NestJS dùng key riêng do NestJS giữ).
- **Không guardrail ở Python.** Repo agent này **không** chặn, không yêu cầu xác nhận, không áp
  hạn mức cho hành động ghi. Việc chặn/ràng buộc do một **repo policy contract riêng** (ngoài repo
  này) đảm nhiệm.
- **Phía Python chỉ log/trace.** Đổi lại việc không gate, repo agent phải **ghi log và trace rõ
  mọi hành động ghi** (tool nào, input gì, kết quả) để audit được khi cần. Tận dụng tầng
  observability hiện có: `core/logging.py` (logging có cấu trúc, correlation id) và
  `infra/observability/langfuse.py` (tracing, với `LANGFUSE_TAGS` ở `core/constants.py`).

## Hệ quả

**Tích cực:**

- Tách bạch mối quan tâm: agent Python tập trung điều phối + quan sát, không gánh logic chính sách
  on-chain; guardrail tập trung ở một nơi chuyên trách (policy contract), tránh rải rác qua nhiều
  giao diện và rủi ro bỏ sót.
- Mọi hành động ghi đều để lại dấu vết log/trace nhất quán phục vụ audit.
- Agent linh hoạt thao tác đầy đủ trên Sui mà không bị kiến trúc Python cản trở.

**Tiêu cực / đánh đổi:**

- An toàn của hành động ghi **phụ thuộc hoàn toàn** vào repo policy contract ngoài; nếu thành phần
  đó vắng mặt hoặc cấu hình sai, không có lớp chặn dự phòng ở phía Python.
- Trách nhiệm log/trace hành động ghi trở thành ràng buộc bắt buộc của repo này — thiếu log đồng
  nghĩa mất khả năng audit.

**Trung tính:**

- Hiện thực hóa đầy đủ phần ghi (và việc trace nó) gắn với **Phase 8**, khi service NestJS và tool
  Sui ghi sẵn sàng; ở v1, sub-agent Sui chưa bật.
- Quyết định này bổ sung cho ADR 0004: ADR 0004 quy định *nơi/cách* truy cập Sui; ADR 0005 quy
  định *phạm vi quyền* và *nơi đặt guardrail*.
