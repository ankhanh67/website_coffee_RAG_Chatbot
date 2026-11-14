# Website Coffee — Multi-Agent System & Hybrid Graph RAG Chatbot

Hệ thống Chatbot AI đa tác tử (Multi-Agent System) cho chuỗi quán cà phê Việt Nam, kết hợp **Jev System One Router**, **LangChain Supervisor & Subagents (`create_agent` + `@tool`)**, và **Hybrid Graph RAG trên Neo4j Aura**.

---

## 1. Kiến trúc tổng thể

```text
User Message
   │
   ▼
[Jev Router (~typesafe/jev-latest)] ──► (ignore) ──► Phản hồi chào hỏi mặc định
   │
   ▼ (order / consultant / faq)
[SemanticCache (Cosine >= 0.90)] ──► (HIT cho consultant / faq) ──► Trả kết quả ngay
   │
   ▼ (MISS hoặc luồng order)
[DeepAgent Supervisor (langchain.agents.create_agent)]
   ├── @tool call_order_agent       ──► OrderAgent (6 @tool: add/update/remove/confirm/cancel/view)
   │                                       └── OrderService (Tính tiền int VNĐ + Xác nhận 2 bước)
   ├── @tool call_consultant_agent  ──► ConsultantAgent (@tool search_menu_and_recommendations)
   │                                       └── HybridRetriever (Neo4j Vector + Graph + Reranker)
   └── @tool call_faq_agent         ──► FAQAgent (@tool search_store_knowledge)
                                           └── HybridRetriever (Neo4j Vector + Graph + Reranker)
```

### Điểm nổi bật:
1. **Phân luồng siêu tốc với Jev (`src/agent/router.py`):** Sử dụng mô hình System One `~typesafe/jev-latest` qua OpenRouter Decisions API (`87.8%` accuracy trên 400 câu test, p50 latency `0.80s`).
2. **LangChain & LangGraph Agents (`create_agent` + `@tool`):**
   - `DeepAgent` đóng vai trò **Supervisor Agent**, có thể gọi một hoặc nhiều Subagent trong cùng một lượt chat khi khách hỏi gộp nhiều ý định.
   - `OrderAgent`, `ConsultantAgent`, `FAQAgent` đều được tạo qua `from langchain.agents import create_agent` và `from langchain.tools import tool`.
   - Thư mục `src/prompt/` chỉ chứa chuỗi System Prompt thuần túy, tách biệt hoàn toàn khỏi logic nghiệp vụ.
3. **Hybrid Graph RAG trên Neo4j Aura (`src/rag/retrieval/`):**
   - **Vector Search:** Truy vấn đồng thời trên `menu_vector_index` (120 món) và `chunk_vector_index` (160 FAQ + 62 đoạn tài liệu) với vector 768 chiều (`google/gemini-embedding-001`).
   - **Graph Traversal:** Mở rộng ngữ cảnh qua cạnh liền kề `[:NEXT]`, cạnh thực thể chung `[:MENTIONS]`, và cầu nối tiêu đề từ FAQ sang Document chunk.
   - **Hybrid Reranker:** Khử trùng lặp, cộng thưởng đa nguồn (`multi_source_bonus`), khớp từ khóa không dấu (`lexical_weight`), đa dạng hóa chủ đề FAQ và cân bằng nguồn.
   - Đạt **100% Answerable Recall@8 (18/18)** và **100% Multi-Chunk Graph Expansion Recall (2/2)** trên bộ `rag_eval_20.json`.
4. **Đặt hàng 2 bước & Tính tiền tất định (`src/services/order_service.py`):**
   - Mọi phép tính đơn giá, số lượng, tổng tiền đều thực hiện bằng số nguyên `int` VNĐ trong Python.
   - Bắt buộc qua bước `PENDING_CONFIRMATION` (liệt kê chi tiết giỏ hàng tạm tính để khách xác nhận) trước khi chuyển sang `CONFIRMED`.
5. **Per-Job Observability (`src/observability/logging.py`):**
   - Mỗi request có `X-Job-ID` riêng và ghi file log độc lập tại `logs/YYYY-MM-DD/<job_id>.log`.

---

## 2. Cài đặt & Cấu hình

### Yêu cầu:
- Python `>= 3.12`
- [`uv`](https://docs.astral.sh/uv/) package manager
- Tài khoản **Neo4j Aura** và **OpenRouter API Key**

### Các bước cài đặt:
```powershell
# 1. Cài đặt dependencies từ uv.lock
uv sync

# 2. Tạo file .env từ .env.example và điền API Key / Neo4j URI
Copy-Item .env.example .env
```

---

## 3. Nạp dữ liệu lên Neo4j Aura (`scripts/ingest.py`)

```powershell
# Nạp toàn bộ Menu (120 món), FAQ (160 câu) và Documents (62 đoạn + Entity + [:NEXT])
.venv\Scripts\python.exe scripts/ingest.py --target all

# Hoặc nạp từng phần:
.venv\Scripts\python.exe scripts/ingest.py --target menu
.venv\Scripts\python.exe scripts/ingest.py --target faq
.venv\Scripts\python.exe scripts/ingest.py --target docs

# Chạy chế độ theo dõi thư mục data/inbox/ tự động nạp file mới (.csv, .docx, .pdf):
.venv\Scripts\python.exe scripts/ingest.py --watch
```

---

## 4. Chạy Server API & Test thủ công

```powershell
.venv\Scripts\uvicorn.exe src.main:app --reload --port 8000
```

- **Giao diện Web Chat trực tiếp:** `http://127.0.0.1:8000/`
- **Chat trực tiếp trên Terminal (CLI):**
  ```powershell
  .venv\Scripts\python.exe scripts/chat_cli.py
  ```
- **Swagger UI:** `http://127.0.0.1:8000/docs`
- **Health Checks:**
  - Liveness: `GET /health/live`
  - Readiness (kiểm tra kết nối Neo4j): `GET /health/ready`
- **Chat Endpoint:** `POST /api/v1/chat`
  ```json
  {
    "session_id": "demo-session-01",
    "message": "Ở Hà Nội những chi nhánh nào có chỗ đỗ ô tô và mấy giờ mở cửa?"
  }
  ```

---

## 5. Kiểm thử & Đánh giá (Tests & Benchmarks)

```powershell
# 1. Kiểm tra chuẩn code với Ruff
.venv\Scripts\ruff.exe check src/ tests/ scripts/ evaluation/

# 2. Chạy toàn bộ Unit Tests & E2E Tests (79 tests)
.venv\Scripts\pytest.exe tests/unit/ tests/e2e/ -v

# 3. Benchmark Jev Router (400 câu router_test.json)
.venv\Scripts\python.exe -m evaluation.router.benchmark_router

# 4. Benchmark Hybrid Graph RAG Retrieval (20 câu rag_eval_20.json)
.venv\Scripts\python.exe -m evaluation.rag.benchmark_retrieval

# 5. Đánh giá End-to-End RAG Generation qua ConsultantAgent & FAQAgent
.venv\Scripts\python.exe -m evaluation.rag.evaluate_rag_e2e
```
