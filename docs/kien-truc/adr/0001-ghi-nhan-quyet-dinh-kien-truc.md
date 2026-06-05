# ADR 0001 — Dùng ADR để ghi nhận quyết định kiến trúc

## Trạng thái

Accepted (Đã chấp thuận) · Ngày: 2026-06-03

## Bối cảnh

Dự án **SuiSwarm Agent** — một swarm đa agent lấy Sui blockchain làm trọng tâm, xây trên
LangGraph — đang được tái cấu trúc từ scaffold ban đầu thành một dự án chuẩn production. Quá
trình này phát sinh nhiều quyết định kiến trúc nền tảng (xem `docs/REFACTORING_PLAN.md`, mục
các quyết định đã chốt D1–D6), định hình toàn bộ codebase và lộ trình triển khai.

Những quyết định như "Sui-first", "multi-agent swarm", "Sui qua service NestJS riêng", "agent
full quyền nhưng không gate ở Python" có ảnh hưởng lâu dài và đôi khi không hiển nhiên với người
mới đọc code. Nếu chỉ lưu trong đầu hoặc rải rác trong chat/PR, lý do (the *why*) sẽ thất lạc:
người sau dễ "sửa lại" một quyết định mà không hiểu vì sao nó được chốt như vậy, hoặc lặp lại
tranh luận đã giải quyết.

`REFACTORING_PLAN.md` là tài liệu sống dạng kế hoạch tổng thể; nó không phải nơi phù hợp để ghi
nhận từng quyết định đơn lẻ kèm bối cảnh và hệ quả một cách bất biến theo thời gian.

## Quyết định

Chúng tôi áp dụng **Architecture Decision Records (ADR)** làm cơ chế chính thức để ghi nhận các
quyết định kiến trúc quan trọng của dự án.

- Mỗi quyết định kiến trúc đáng kể được ghi thành **một file ADR riêng** dưới
  `docs/kien-truc/adr/`, đánh số tuần tự (`0001`, `0002`, ...).
- ADR viết bằng **tiếng Việt** (nhất quán với quyết định D4 — toàn bộ `docs/` tiếng Việt),
  thuật ngữ kỹ thuật giữ nguyên tiếng Anh khi đó là chuẩn ngành.
- Mỗi ADR theo cấu trúc cố định: **Tiêu đề, Trạng thái, Bối cảnh, Quyết định, Hệ quả**.
- **Trạng thái** dùng các giá trị quy ước: `Proposed` (đề xuất), `Accepted` (đã chấp thuận),
  `Superseded` (bị thay thế — ghi rõ bởi ADR nào), `Deprecated` (ngừng dùng).
- ADR là **bất biến (immutable)** sau khi `Accepted`: không sửa nội dung quyết định cũ; nếu
  quyết định thay đổi, **tạo ADR mới** và đánh dấu ADR cũ là `Superseded`.
- ADR này (0001) khởi xướng quy ước; các quyết định nền tảng D1–D6 được ghi thành ADR 0002–0005
  (cùng ADR khác khi cần).

## Hệ quả

**Tích cực:**

- Lý do của mỗi quyết định được lưu lại lâu dài, có ngữ cảnh, dễ tra cứu cho người mới.
- Tránh lặp lại tranh luận đã giải quyết; thay đổi quyết định trở nên có chủ đích (phải viết ADR
  mới thay thế thay vì lặng lẽ sửa code).
- Khớp với mục tiêu tài liệu trong `REFACTORING_PLAN.md` (Phase 7: viết đầy đủ ADR ghi lại D1–D6)
  và quy ước "quyết định lớn ghi thành ADR" ở phụ lục quy ước.

**Tiêu cực / đánh đổi:**

- Phát sinh chi phí viết tài liệu cho mỗi quyết định lớn; cần kỷ luật để ADR không bị bỏ rơi.
- Cần thống nhất tiêu chí "đáng kể" để tránh hoặc viết ADR cho mọi thứ vụn vặt, hoặc bỏ sót
  quyết định quan trọng.

**Trung tính:**

- Thư mục `docs/kien-truc/adr/` trở thành nơi chính thức chứa lịch sử quyết định; cần được tham
  chiếu trong onboarding và khi review các thay đổi kiến trúc.
