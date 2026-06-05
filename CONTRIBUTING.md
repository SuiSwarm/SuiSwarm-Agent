# Đóng góp cho SuiSwarm Agent

Cảm ơn bạn đã đóng góp! Tài liệu này tóm tắt quy trình và quy ước.

## Thiết lập môi trường

```bash
uv venv && . .venv/bin/activate        # hoặc .venv\Scripts\Activate.ps1 trên Windows
uv pip install -e ".[dev]"
cp .env.example .env                   # rồi điền OPENAI_API_KEY
pre-commit install
```

## Cổng chất lượng (chạy trước khi mở PR)

```bash
make check      # = ruff check + mypy + pytest
# hoặc từng bước:
make lint
make format     # tự sửa định dạng
make type
make test
```

CI (`.github/workflows/ci.yml`) chạy đúng các bước này trên Python 3.11–3.13. PR chỉ merge
khi CI xanh.

## Quy ước

- **Style/format/lint:** ruff (cấu hình trong `pyproject.toml`). **Type:** mypy, không để hàm
  thiếu type trong `src/`.
- **Commit:** [Conventional Commits](https://www.conventionalcommits.org/) (vd `feat:`, `fix:`,
  `refactor:`). Nhánh feature ngắn → PR.
- **Async:** code I/O-bound viết `async`; tool expose async khi client bên dưới là async.
- **Cấu hình:** không đọc `os.environ` trực tiếp — luôn qua `get_settings()`.
- **Lỗi:** không nuốt `except Exception` mà không log; dùng cây exception trong `core/exceptions.py`.

## Thêm một tool

1. Viết logic trong `service.py` của domain tương ứng (vd `tools/market/coingecko/service.py`).
2. Bọc bằng `@tool` mỏng trong `tools.py` cùng thư mục.
3. Thêm vào danh sách tool và (nếu cần) nhóm trong `tools/registry.py`.
4. Viết unit test (mock HTTP bằng `respx`).

## Thêm một sub-agent

1. Tạo `agent/agents/<ten>.py` dùng `build_worker_agent(...)` với prompt + toolset.
2. Đăng ký builder trong `agent/graph.py` (`_BUILDERS`) và prompt trong `agent/prompts.py`.

Xem thêm `docs/` để hiểu kiến trúc tổng thể.
