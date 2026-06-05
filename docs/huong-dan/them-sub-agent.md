# Hướng dẫn: Thêm một sub-agent mới

> Trạng thái: Tài liệu hướng dẫn · Ngôn ngữ: Tiếng Việt
>
> Tài liệu này mô tả cách thêm một **sub-agent** mới vào swarm SuiSwarm đúng theo pattern
> hiện có. Bám sát các quyết định D1-D6 và `docs/REFACTORING_PLAN.md`. Thuật ngữ kỹ thuật
> (sub-agent, supervisor, ReAct, tool, prompt...) giữ nguyên tiếng Anh khi là chuẩn ngành.

---

## 1. Sub-agent trong SuiSwarm là gì

Theo quyết định **D2 (multi-agent swarm)**, kiến trúc gồm:

- **Supervisor** (`agent/supervisor.py`, dùng `langgraph_supervisor.create_supervisor`):
  điều phối, phân việc cho các sub-agent rồi tổng hợp câu trả lời cuối.
- **Sub-agent**: mỗi sub-agent là một **agent ReAct** được dựng bằng
  `create_react_agent` (qua factory `build_worker_agent` trong `agent/agents/base.py`).

Điểm cốt lõi: sub-agent ReAct **tự chain tool của chính nó** trong nhiều vòng. Ví dụ
market_agent có thể tự thực hiện chuỗi "resolve id → fetch details" mà không cần supervisor
can thiệp giữa chừng — khác hẳn planner một lượt cũ. Bạn không phải viết vòng lặp tool;
`create_react_agent` lo phần đó. Việc của bạn chỉ là: **chọn tool + viết prompt + đặt tên +
đăng ký**.

Mỗi sub-agent có một tên ổn định trong `core/constants.py` (`AgentName`), dùng cho routing,
tracing và handoff.

---

## 2. Bốn bước thêm một sub-agent

Ví dụ minh hoạ: thêm sub-agent **`analytics`** (giả định) dùng nhóm tool đã có.

### Bước 1 — Khai báo tên trong `core/constants.py`

Thêm một thành viên vào enum `AgentName` (giá trị là tên ổn định mà supervisor dùng):

```python
# src/suiswarm_agent/core/constants.py
class AgentName(StrEnum):
    SUPERVISOR = "supervisor"
    SUI_ONCHAIN = "sui_onchain_agent"
    MARKET = "market_agent"
    RESEARCH = "research_agent"
    ANALYTICS = "analytics_agent"   # <-- thêm dòng này
```

### Bước 2 — Thêm prompt vào `agent/prompts.py`

Mỗi sub-agent có một system prompt riêng. **Viết prompt bằng tiếng Anh** (model hoạt động
tốt hơn) nhưng luôn yêu cầu agent trả lời theo ngôn ngữ của người dùng — đúng quy ước các
prompt hiện có:

```python
# src/suiswarm_agent/agent/prompts.py
ANALYTICS_PROMPT = """You are the analytics agent for SuiSwarm. Answer quantitative \
analysis questions using your tools.

Guidance:
- Resolve identifiers first when needed, then chain the tool calls required to fully \
answer the request.
- Never fabricate figures; rely on tool outputs. If a tool fails, say so with the reason.
- Be concise and concrete. Reply in the user's language.
"""
```

### Bước 3 — Tạo `agent/agents/<ten>.py` dùng `build_worker_agent`

Tạo file builder. Đi theo đúng khuôn của `agent/agents/market.py` /
`agent/agents/sui_onchain.py`: chọn nhóm tool từ registry, rồi gọi `build_worker_agent`.
Luôn kèm `system_tools(settings)` để agent có sẵn các tiện ích (ví dụ `get_utc_time`).

```python
# src/suiswarm_agent/agent/agents/analytics.py
"""Analytics sub-agent."""

from __future__ import annotations

from langgraph.graph.state import CompiledStateGraph

from suiswarm_agent.agent.agents.base import build_worker_agent
from suiswarm_agent.agent.prompts import ANALYTICS_PROMPT
from suiswarm_agent.config.settings import Settings
from suiswarm_agent.core.constants import AgentName
from suiswarm_agent.tools.registry import market_tools, system_tools


def build_analytics_agent(settings: Settings | None = None) -> CompiledStateGraph:
    tools = [*market_tools(settings), *system_tools(settings)]
    return build_worker_agent(
        name=AgentName.ANALYTICS,
        tools=tools,
        prompt=ANALYTICS_PROMPT,
    )
```

Ghi chú:

- `build_worker_agent` mặc định dùng `role="worker"` cho LLM (xem `llm/factory.py`); chỉ
  truyền `role` khác nếu thực sự cần.
- Sub-agent **không** compile kèm checkpointer — persistence do graph supervisor sở hữu khi
  nó được compile (xem `agent/graph.py`).

Rồi export builder trong `agent/agents/__init__.py`:

```python
# src/suiswarm_agent/agent/agents/__init__.py
from suiswarm_agent.agent.agents.analytics import build_analytics_agent
# ...

__all__ = [
    "build_analytics_agent",   # <-- thêm
    "build_market_agent",
    "build_research_agent",
    "build_sui_onchain_agent",
    "build_worker_agent",
]
```

### Bước 4 — Đăng ký builder trong `agent/graph.py` (`_BUILDERS`) và bật qua `AGENT__ENABLED_AGENTS`

Thêm builder vào map `_BUILDERS` trong `agent/graph.py`. Key của map chính là tên bạn dùng
trong biến môi trường `AGENT__ENABLED_AGENTS`:

```python
# src/suiswarm_agent/agent/graph.py
from suiswarm_agent.agent.agents import (
    build_analytics_agent,   # <-- thêm import
    build_market_agent,
    build_research_agent,
    build_sui_onchain_agent,
)

_BUILDERS: dict[str, Callable[[Settings | None], CompiledStateGraph]] = {
    "market": build_market_agent,
    "research": build_research_agent,
    "sui": build_sui_onchain_agent,
    "analytics": build_analytics_agent,   # <-- thêm dòng này
}
```

Cập nhật system prompt của supervisor trong `agent/prompts.py` (`SUPERVISOR_PROMPT`) để
thêm mô tả sub-agent mới vào danh sách "Sub-agents you can delegate to" — nếu không
supervisor sẽ không biết để uỷ thác.

Cuối cùng **bật** sub-agent qua cấu hình. Mặc định `enabled_agents = ["market", "research"]`.
Để thêm `analytics`, đặt biến môi trường:

```bash
AGENT__ENABLED_AGENTS=market,research,analytics
```

Lưu ý cơ chế bật tự động: agent **`sui`** không cần liệt kê thủ công — `agent/graph.py` tự
thêm `sui` khi service NestJS được cấu hình (`SUI_SERVICE__BASE_URL`, theo D5). Với sub-agent
thường (không gắn service ngoài), bạn bật bằng cách liệt kê tên trong `AGENT__ENABLED_AGENTS`.

Nếu một key trong `enabled_agents` không có trong `_BUILDERS`, graph chỉ log cảnh báo và bỏ
qua key đó; nếu không còn agent nào được bật, `build_graph` raise `ConfigError`.

---

## 3. Checklist trước khi mở PR

- [ ] Tên agent thêm vào `AgentName` (`core/constants.py`).
- [ ] Prompt riêng trong `agent/prompts.py` (tiếng Anh, yêu cầu trả lời theo ngôn ngữ user).
- [ ] File builder `agent/agents/<ten>.py` dùng `build_worker_agent` + `system_tools`.
- [ ] Export builder trong `agent/agents/__init__.py`.
- [ ] Đăng ký builder trong `_BUILDERS` của `agent/graph.py` (key = tên dùng trong env).
- [ ] Cập nhật `SUPERVISOR_PROMPT` để supervisor biết uỷ thác cho agent mới.
- [ ] Bật qua `AGENT__ENABLED_AGENTS` (nếu là agent thường); agent gắn service ngoài có thể
      tự bật theo cấu hình service.
- [ ] Bổ sung test tích hợp graph nếu cần (tham khảo `tests/integration/test_graph.py`); LLM
      không bao giờ được gọi thật trong test.
- [ ] Qua đủ cổng CI: `ruff check`, `ruff format --check`, `mypy`, `pytest`.

---

## 4. Tham chiếu nhanh

- Factory ReAct (`create_react_agent`): `src/suiswarm_agent/agent/agents/base.py`
- Builder mẫu: `src/suiswarm_agent/agent/agents/market.py`,
  `src/suiswarm_agent/agent/agents/sui_onchain.py`
- Prompts: `src/suiswarm_agent/agent/prompts.py`
- Lắp ráp graph + `_BUILDERS` + tự bật `sui`: `src/suiswarm_agent/agent/graph.py`
- Supervisor (`create_supervisor`): `src/suiswarm_agent/agent/supervisor.py`
- Tên agent ổn định: `src/suiswarm_agent/core/constants.py` (`AgentName`)
- Đăng ký tool theo nhóm (dùng để cấp tool cho agent): `src/suiswarm_agent/tools/registry.py`
- Test graph mẫu: `tests/integration/test_graph.py`
