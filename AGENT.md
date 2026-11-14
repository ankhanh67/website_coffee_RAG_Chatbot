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
  - `NEO4J_URI`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`: Đã kết nối Neo4j Aura thật và nạp đầy đủ 120 món menu.

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
- **[x] Phase 3 — Kết nối Neo4j Aura & Nạp dữ liệu Menu (`menu.csv`):**
  - **[x] Feature 3.1 — Neo4j Client, Schema & Repository** (Commit `23bde3d`).
  - **[x] Feature 3.2 — Embeddings & Menu Ingestion (`scripts/ingest.py`):**
    - `src/rag/embeddings.py` (`EmbeddingsClient` gọi OpenRouter embedding model `google/gemini-embedding-001` 768 dimensions).
    - `src/rag/ingestion/base.py`, `src/rag/ingestion/menu.py` (`MenuIngestor` parse CSV và tạo dense semantic text mô tả món).
    - `scripts/ingest.py` hỗ trợ `--target menu`.
    - Đã nạp thành công **120/120 món ăn/đồ uống**, **10 danh mục (Category)**, **120 quan hệ `[:BELONGS_TO]`**, và tạo Vector Index `menu_vector_index` trên Neo4j Aura.
    - Bổ sung thuộc tính `m.name = $name_vi` trên `MenuItem` để Neo4j Aura hiển thị tên món làm caption mặc định.
- **[x] Phase 4 — Hoàn thiện Order Agent (Luồng đặt hàng & Xác nhận 2 bước):**
  - Mở rộng `ModelClient` (`generate_structured`, `generate_text`) và `src/schema/order.py` (`OrderExtraction`, `OrderStatus`, `VIEW`, `UNKNOWN`).
  - Bổ sung `find_menu_item_by_text` và `find_menu_item_by_vector` trong `Neo4jRepository` (Phương án A: Cypher Text Match + Vector Search Fallback `>= 0.82`).
  - Xây dựng `OrderService` (`src/services/order_service.py`): xử lý từ đồng nghĩa phổ biến, tự động lấy `price_m` cho 46 món `"Một cỡ"`, tính tiền tất định bằng số nguyên `int` VNĐ, quản lý trạng thái giỏ hàng (`PENDING_CONFIRMATION` -> `CONFIRMED` / `CANCELLED`).
  - Xây dựng `OrderAgent` (`src/subagents/order_agent.py`) và `src/prompt/order_agent.py`: luôn liệt kê chi tiết giỏ hàng tạm tính và hỏi khách xác nhận trước khi chốt đơn; `DeepAgent` tự động chuyển tiếp câu trả lời xác nhận ngắn (`"Đúng rồi"`, `"Ok chốt nhé"`) vào `OrderAgent` khi phiên đang có đơn chờ xác nhận.
  - Toàn bộ 54/54 tests (`unit` + `e2e`) pass, `ruff check` sạch.
- **[x] Phase 5 — Nạp dữ liệu FAQ, Documents & Watch Mode lên Neo4j Aura:**
  - `src/schema/retrieval.py`: Thêm `ChunkRecord`, `EntityRecord`.
  - `src/rag/graph/queries.py` & `src/rag/graph/repository.py`: Thêm constraints cho Chunk và Entity, tạo `chunk_vector_index` (768d), lệnh upsert chunk, nối `[:NEXT]` và `[:MENTIONS]`.
  - `src/rag/ingestion/faq.py` (`FAQIngestor`): Nạp thành công **160/160 câu FAQ**.
  - `src/rag/ingestion/entity_deduplicator.py` & `entity_extractor.py`: Thuật toán Jaccard token similarity ($\ge 0.50$) hợp nhất chi nhánh, phương thức thanh toán và mã khuyến mãi.
  - `src/rag/ingestion/chunker.py` & `document.py` (`DocumentIngestor`): Nạp thành công **62/62 đoạn tài liệu** từ `doc_sections_manifest.json`, nối **58 quan hệ `[:NEXT]`** và các quan hệ `[:MENTIONS]` tới `Entity`.
  - `src/rag/ingestion/watcher.py` (`InboxWatcher`): Lắng nghe `data/inbox/` tự động nạp file mới (`.docx`, `.pdf`, `.csv`).
  - Mở rộng CLI `scripts/ingest.py` hỗ trợ `--target [menu|faq|docs|all]` và `--watch`. Đã nạp thành công trên Neo4j Aura thật.
  - Toàn bộ 67/67 tests (`unit` + `e2e`) pass, `ruff check` sạch.
  - **Refactor Loại bỏ Regex & Trao quyền cho LLM (LLM-first Ingestion):**
    - Chuyển `EntityExtractor` sang gọi `ModelClient.generate_structured` với Gemini 2.5 Flash, bóc tách thực thể mở (Branch, Payment, Promotion, Ingredient, Facility, Policy, General) tự động mà không dùng regex hay list từ khóa cứng.
    - Loại bỏ `_SHORT_FOLLOWUP_RE` trong `src/prompt/order_agent.py` và `src/agent/deep_agent.py`, để LLM tự phân loại intent câu ngắn khi có pending order.
    - Loại bỏ `_LEADING_CLASSIFIER_RE` trong `src/services/order_service.py`, để OrderAgent LLM trích xuất tên món chuẩn hóa.
  - **Refactor Tích hợp LangChain & LangGraph:**
    - Bổ sung `langchain`, `langchain-core`, `langchain-openai`, `langgraph` vào `pyproject.toml`.
    - Tạo `src/agent/llm.py` xây dựng LCEL chains (`ChatPromptTemplate | ChatOpenAI | StrOutputParser | RunnableLambda`).
    - Cập nhật `ModelClient` (`src/infrastructure/model_client.py`) dùng `ChatOpenAI` và LCEL chains cho `generate_text` & `generate_structured` (giữ Jev Decisions API cho `decide()`).
    - Cập nhật `EmbeddingsClient` (`src/rag/embeddings.py`) dùng `OpenAIEmbeddings` của `langchain_openai`.
    - Cập nhật `DeepAgent` (`src/agent/deep_agent.py` + `src/prompt/deep_agent.py`) sang kiến trúc **Supervisor Agent** dùng `from langchain.agents import create_agent` và `from langchain.tools import tool` (bọc các Subagent thành 3 `@tool`: `call_order_agent`, `call_consultant_agent`, `call_faq_agent`), kết hợp Jev lọc `ignore` ở đầu.
    - Cập nhật `OrderAgent` (`src/subagents/order_agent.py`) dùng `from langchain.agents import create_agent` và `from langchain.tools import tool` với 6 `@tool` (`add_order_items`, `update_order_items`, `remove_order_items`, `confirm_order`, `cancel_order`, `view_order`).
    - Toàn bộ 68/68 tests pass, `ruff check` sạch.
- **[x] Phase 6 — Hybrid Graph RAG (Vector Search + Graph Traversal + Reranker):**
  - `src/schema/retrieval.py`: Thêm `RetrievedItem` và `HybridRetrievalResult`.
  - `src/rag/graph/queries.py` & `src/rag/graph/repository.py`: Thêm `SEARCH_CHUNKS_BY_VECTOR`, `SEARCH_MENU_ITEMS_BY_VECTOR`, `EXPAND_CHUNKS_NEXT` (mở rộng 2 chiều qua `[:NEXT]`), `EXPAND_CHUNKS_BY_ENTITIES` (mở rộng qua `[:MENTIONS]`), và `EXPAND_CHUNKS_BY_TITLE_MENTION` (cầu nối ngữ nghĩa từ FAQ sang Document chunk kèm trọng số `mention_count`).
  - `src/rag/retrieval/`:
    - `base.py` (`BaseRetriever`), `vector_search.py` (`VectorSearcher` tìm đồng thời trên `chunk_vector_index` và `menu_vector_index`, chuẩn hóa `source_type` cho `doc-*` / `faq-*`).
    - `graph_search.py` (`GraphSearcher` mở rộng theo `[:NEXT]`, `[:MENTIONS]` và cầu nối tiêu đề).
    - `reranker.py` (`HybridReranker` hợp nhất kết quả Vector + Graph, cộng thưởng lexical overlap không dấu và multi-source confirmation, đa dạng hóa `topic_id` của FAQ và cân bằng slot giữa `document`, `menu`, `faq`).
    - `hybrid_search.py` (`HybridRetriever` điều phối toàn bộ pipeline và kiểm tra ngưỡng `evidence_threshold` cho câu hỏi ngoài phạm vi).
  - Benchmark `evaluation/rag/benchmark_retrieval.py` trên 20 câu `data/evaluation/rag_eval_20.json` với Neo4j Aura thật:
    - **Answerable Recall@8: 18/18 (100.0%)**
    - **Multi-Chunk Graph Expansion Recall: 2/2 (100.0%)** (bao gồm `Q17` nối `policy-08` + `policy-09` và `Q18` nối `branch-07` + `branch-08`).
  - Toàn bộ 73/73 tests (`unit` + `e2e`) pass, `ruff check` sạch.
- **[x] Phase 7 — Consultant Agent & FAQ Agent (Grounding + Citation + LangChain `create_agent`):**
  - `src/prompt/consultant_agent.py` & `src/prompt/faq_agent.py`: Chứa duy nhất chuỗi System Prompt thuần túy, quy định bắt buộc gọi tool truy xuất dữ liệu, bám sát kết quả từ `HybridRetriever` và từ chối lịch sự khi câu hỏi ngoài phạm vi (`has_sufficient_evidence=False`).
  - `src/subagents/consultant_agent.py`: Xây dựng `ConsultantAgent` bằng `from langchain.agents import create_agent` và `@tool` (`search_menu_and_recommendations`).
  - `src/subagents/faq_agent.py`: Xây dựng `FAQAgent` bằng `from langchain.agents import create_agent` và `@tool` (`search_store_knowledge`).
  - `src/api/dependencies.py`: Thay thế hoàn toàn các stub bằng 3 agent thật (`OrderAgent`, `ConsultantAgent`, `FAQAgent`) dùng chung `HybridRetriever` và `ModelClient`.
  - `tests/unit/subagents/test_consultant_and_faq_agents.py`: Toàn bộ 76/76 tests (`unit` + `e2e`) pass, `ruff check` sạch.
- **[x] Phase 8 — Semantic Cache, End-to-End Evaluation & Final Polish:**
  - `src/rag/cache/semantic_cache.py`: Triển khai `SemanticCache` (cosine similarity $\ge 0.90$, TTL `3600s`) cho `CONSULTANT` và `FAQ`, tuyệt đối không cache `ORDER`.
  - `src/agent/deep_agent.py` & `src/api/dependencies.py`: Tích hợp `SemanticCache` vào `DeepAgent`.
  - `src/main.py`: Bổ sung `/health/ready` kiểm tra kết nối Neo4j Aura và đóng kết nối sạch sẽ trong `lifespan`.
  - `evaluation/rag/evaluate_rag_e2e.py`: Script đánh giá End-to-End 20 câu `rag_eval_20.json` đi qua `ConsultantAgent` và `FAQAgent`.
  - `README.md`: Tài liệu hóa đầy đủ kiến trúc, hướng dẫn cài đặt, nạp dữ liệu, chạy server và kiểm thử.
  - Toàn bộ **79/79 tests (`unit` + `e2e`) pass**, `ruff check` sạch.
- **[x] Phase 9 — Conversation Memory (`InMemorySaver`) & Giao diện Web/CLI Chat:**
  - Tích hợp `langgraph.checkpoint.memory.InMemorySaver` vào `DeepAgent`, `OrderAgent`, `ConsultantAgent` và `FAQAgent` theo `thread_id` gắn với `session_id`, giúp nhớ ngữ cảnh hội thoại nhiều lượt ("món đó", "chi nhánh đấy", "lấy mình 1 ly đó size L").
  - Tạo giao diện Web Chat trực quan tại `GET /` (`src/api/routes/ui.py`) và CLI Chat (`scripts/chat_cli.py`).
  - Toàn bộ **81/81 tests (`unit` + `e2e`) pass**, `ruff check` sạch.

