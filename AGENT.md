# AGENT.md — Context & Handover Notes for AI Agents

Tài liệu này lưu lại toàn bộ quyết định kỹ thuật, trạng thái hiện tại của dự án, lưu ý môi trường và quy tắc làm việc của user. **Mọi session mới phải đọc file này trước khi code và cập nhật lại sau mỗi thay đổi quan trọng.**

---

## 1. Quy tắc làm việc bắt buộc (Workflow Rules)
1. **Commit theo từng feature / bugfix nhỏ:** Không đợi hết cả Phase mới commit. Mỗi khi thêm một feature nhỏ hoặc sửa lỗi xong và pass test là tạo commit ngay. Commit message chỉ viết **1 dòng cực ngắn gọn** (ví dụ: `feat/add logging`, `fix/...`).
2. **Báo nội dung commit trước khi `git push`:** Luôn hiển thị rõ commit message (và danh sách file chính) cho user xem trước khi đẩy lên `origin/main`.
3. **Cập nhật `AGENT.md`:** Sau mỗi phần hoàn thành hoặc khi có quyết định/lưu ý mới, cập nhật ngay vào file này để session sau nắm được context.
4. **Quản lý package bằng `uv`:** Luôn dùng `uv` (`.venv\Scripts\python.exe`, `uv add`, `uv sync`), không dùng `pip` trực tiếp.

---

## 2. Quyết định kiến trúc & Công nghệ (Key Decisions)
- **LLM Provider:** Dùng **OpenRouter** (`https://openrouter.ai/api/v1`) với 1 API key duy nhất (`LLM_API_KEY` trong `.env`).
  - Generator model mặc định: `google/gemini-2.5-flash`.
- **Router (Phân loại intent 4 luồng `order`, `consultant`, `faq`, `ignore`):**
  - Không dùng LLM sinh chữ truyền thống để tiết kiệm token và giảm độ trễ.
  - Dùng mô hình **Jev** của TypeSafe AI (`~typesafe/jev-latest`, thuộc nhóm *System One* trả về dữ liệu định kiểu `choice` kèm `probabilities` và `confidence`).
  - Gọi qua OpenRouter Decisions API: `POST https://openrouter.ai/api/alpha/decisions` (cùng `LLM_API_KEY`).
  - **Fallback:** Khi Jev lỗi/timeout hoặc `confidence < ROUTER_CONFIDENCE_THRESHOLD` (`0.5`), trả về `RouterAction.IGNORE` (`is_fallback=True`), không tốn thêm token gọi LLM.
- **HTTP Client:** Dùng `httpx2` (dependency sẵn có của `openai>=3.x` trong `.venv`) cho `ModelClient`.
- **Dữ liệu (`data/`):**
  - Đã lọc 10 file cần thiết từ `fi_ai_mas_llm_dataset/data_pack` sang `data/raw/` và `data/evaluation/`.
  - Thư mục gốc `fi_ai_mas_llm_dataset/` đã được xóa theo quyết định của user; `data/raw/` và `data/evaluation/` được track trực tiếp trên Git (`data/processed/` và `data/inbox/` bị ignore).
- **GitHub Remote:** `https://github.com/ankhanh67/website_coffee_RAG_Chatbot.git` (nhánh `main`).

---

## 3. Lưu ý môi trường (Environment Quirks)
- **Windows Sandbox & `asyncio`:** Trong sandbox của Antigravity trên Windows, việc khởi tạo `asyncio` event loop (`_make_self_pipe` qua loopback socket) bị treo. Vì vậy khi chạy `pytest` cho các hàm `async` hoặc gọi mạng (`OpenRouter`, `git push`), cần chạy với `BypassSandbox: true`.
- **Cấu hình `.env` hiện tại:**
  - `LLM_API_KEY`: Đã có key OpenRouter thật và hoạt động tốt.
  - `NEO4J_URI`, `NEO4J_PASSWORD`: Vẫn đang là placeholder (`neo4j+s://xxxxxxxx...`), sẽ cần cập nhật trước khi sang Phase 3.

---

## 4. Trạng thái tiến độ (Progress Log)
- **[x] Phase 0 — Khởi tạo Repository & Lọc dữ liệu** (Commit `0b62673`, `96ee3fd`):
  - `pyproject.toml`, `.env.example`, `.gitignore`, `src/config.py`, `src/exceptions.py`, `src/main.py` (`/health/live`), `scripts/prepare_data.py`, `tests/unit/test_config.py`.
- **[x] Phase 1 — Core Schemas & Jev Router** (Commit `72eade5`):
  - `src/schema/common.py`, `src/schema/router.py`, `src/schema/chat.py`.
  - `src/prompt/router.py` (Jev `choice` question cho 4 route).
  - `src/infrastructure/model_client.py` (`decide()` có retry + exponential backoff).
  - `src/agent/router.py` + unit tests `tests/unit/agent/test_router.py` (18/18 tests pass).
  - Benchmark `evaluation/router/benchmark_router.py` trên 400 câu `router_test.json`:
    - Độ chính xác baseline: **87.8% (351/400)** (`ignore`: 95%, `consultant`: 90%, `order`: 84%, `faq`: 82%).
    - Latency: p50 = `0.80s`, p95 = `0.97s`. Tổng chi phí 400 câu: `$0.00931`.
    - Điểm có thể cải thiện sau: các câu hỏi phương thức thanh toán kèm tính tiền (*"Thanh toán bằng QR được không em, tính tiền giúp cô"*) đang bị Jev phân vào `faq` thay vì `order`.
- **[x] Phase 2 — Luồng API & Orchestrator tối thiểu (Vertical Slice đầu tiên):**
  - **[x] Feature 2.1 — Subagents Base, Domain Schemas & DeepAgent Orchestrator** (Commit `9284a55`).
  - **[x] Feature 2.2 — ChatService & FastAPI `/api/v1/chat` endpoint + DI** (Commit `7db1b45`).
  - **[x] Feature 2.3 — Per-Job File Logging (`src/observability/logging.py`):**
    - Mỗi request/job có `job_id` riêng qua `contextvars` (`job_context`), ghi toàn bộ các bước của job đó vào `logs/YYYY-MM-DD/<job_id>.log` và trả header `X-Job-ID`.
    - Bổ sung log xuyên suốt `ChatService` -> `DeepAgent` -> `Router` -> `ModelClient`.
- **[~] Phase 3 — Kết nối Neo4j Aura & Nạp dữ liệu Menu (`menu.csv`):**
  - **[x] Feature 3.1 — Neo4j Client, Schema & Repository:**
    - `src/schema/retrieval.py` (`MenuItemRecord`, `VectorSearchResult`).
    - `src/rag/graph/queries.py` (Cypher queries cho uniqueness constraints, vector index, upsert món + category `BELONGS_TO`, get món theo ID).
    - `src/rag/graph/client.py` (`Neo4jClient` quản lý connection pool & session bất đồng bộ).
    - `src/rag/graph/repository.py` (`Neo4jRepository` thực thi Cypher, bọc `RetrievalError` và ghi log chi tiết từng stage).
    - Unit tests: `tests/unit/rag/test_retrieval_schema.py`, `tests/unit/rag/test_queries_syntax.py`, `tests/unit/rag/test_neo4j_repository.py` (tổng suite: 39/39 tests pass).
  - **[ ] Feature 3.2 — Embeddings & Menu Ingestion Script (`scripts/ingest.py`):** Bước tiếp theo.

