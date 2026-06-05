# ADR 0004 — Tương tác Sui qua service NestJS (REST)

## Trạng thái

Accepted (Đã chấp thuận) · Ngày: 2026-06-03 · Hiện thực hóa quyết định D5

## Bối cảnh

SuiSwarm Agent lấy Sui blockchain làm domain lõi (D1). Có hai hướng để agent Python tương tác với
Sui:

1. **Trực tiếp trong Python** — dùng một SDK như pysui để gọi Sui RPC, tự quản ví/khóa riêng, tự
   ký và gửi giao dịch ngay trong repo này.
2. **Qua một service trung gian** — đặt toàn bộ logic Sui (RPC, giữ key, ký tx) ở một service
   riêng, và agent Python chỉ gọi service đó qua REST.

Việc giữ khóa riêng (private key) của ví agent và ký giao dịch là phần nhạy cảm nhất về bảo mật.
Nếu để khóa và logic ký nằm chung trong repo agent Python, bề mặt tấn công và rủi ro rò rỉ key
tăng cao; đồng thời nó trộn mối quan tâm "điều phối agent / gọi LLM" với "custody & ký tx
on-chain". Hệ sinh thái Sui/TypeScript cũng thành thục cho phần on-chain, phù hợp triển khai bằng
NestJS.

## Quyết định

Mọi tương tác Sui được đặt trong **một service NestJS riêng**; phía Python **gọi qua REST API**,
**không gọi Sui RPC trực tiếp** và **không dùng pysui** (D5).

- **Không giữ key ở Python.** Service NestJS giữ ví/khóa riêng của agent, ký và gửi giao dịch, và
  là bên duy nhất nói chuyện với Sui RPC.
- **Client mỏng phía Python** — `tools/sui/{client,service,tools}.py`: `SuiServiceClient` là HTTP
  client gọi REST của NestJS (chạy trên `AsyncHttpClient` chung, giống cách gọi CoinGecko). Tool
  hướng LLM là `sui_service_request` (mỏng); service map sang endpoint NestJS; không có logic Sui
  nào trong thân tool.
- **Đăng ký có điều kiện.** Tool Sui chỉ được đăng ký khi `SUI_SERVICE__BASE_URL` có giá trị; nếu
  thiếu, sub-agent Sui tự ẩn (degrade mượt). Graph tự bật sub-agent Sui khi service được cấu hình.
- **Auth bằng API key ở header** — cấu hình qua `SUI_SERVICE__BASE_URL`, `SUI_SERVICE__API_KEY`,
  `SUI_SERVICE__API_KEY_HEADER` (gom trong `SuiServiceSettings` của `config/settings.py`).
- **Lỗi từ service** được map vào cây exception domain (`SuiServiceError`, cùng `UpstreamAPIError`
  / `RateLimitedError` của tầng HTTP).
- **Nguồn contract**: ưu tiên OpenAPI/Swagger của NestJS để sinh/mirror DTO khi service sẵn sàng.

Ranh giới luồng:

```
tools/sui  ──HTTP/REST──►  Service NestJS (repo khác)  ──Sui RPC──►  Sui blockchain
```

## Hệ quả

**Tích cực:**

- Khóa riêng và logic ký tx không bao giờ nằm trong repo agent Python → giảm bề mặt rủi ro bảo mật,
  tách bạch custody khỏi điều phối agent.
- `tools/sui/*` đối xứng với các domain market (cùng mô hình client/service/tool trên
  `AsyncHttpClient` chung) → dễ test bằng `respx` mock REST của NestJS, không cần node Sui thật.
- Degrade mượt: thiếu `SUI_SERVICE__*` thì agent v1 vẫn chạy bằng market + research.

**Tiêu cực / đánh đổi:**

- Thêm một service ngoài repo (NestJS) cùng một network hop (REST) → thêm độ trễ và một thành phần
  cần vận hành/triển khai.
- Phụ thuộc vào contract của NestJS; trong khi service chưa dựng, `tools/sui/*` chỉ là seam (chỗ
  cắm sẵn) — Sui tích hợp đầy đủ ở **Phase 8**.

**Trung tính:**

- DTO phía Python (`tools/sui/models`) cần đồng bộ với NestJS (ưu tiên sinh từ OpenAPI) để tránh
  lệch contract theo thời gian.
- Quyết định này chỉ định *nơi* logic Sui sống và *cách* Python truy cập; *phạm vi quyền* của agent
  với Sui và cơ chế guardrail được quy định riêng ở ADR 0005 (D6).
