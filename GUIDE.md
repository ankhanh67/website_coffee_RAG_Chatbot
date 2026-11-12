# Website Coffee MAS-LLM: Project Skeleton & Implementation Roadmap (API-First Edition)

**Mục đích:** Tài liệu này định nghĩa cấu trúc mã nguồn chuẩn (skeleton), trách nhiệm của từng file, ranh giới phụ thuộc (dependency boundaries), chiến lược lọc dữ liệu từ `fi_ai_mas_llm_dataset`, và thứ tự triển khai từng bước (phases) để xây dựng hệ thống Multi-Agent LLM cho `website_coffee` trên Antigravity IDE.

**Nguyên tắc cốt lõi:**
1. **API-First LLM:** Không thực hiện huấn luyện mô hình (SFT/Quantization). Toàn bộ tác vụ Router, Intent Extraction, Entity Extraction và Generation đều sử dụng LLM API (OpenAI / Gemini / tương đương) kết hợp ép kiểu đầu ra (Structured Outputs / Pydantic).
2. **Cloud Graph RAG:** Sử dụng **Neo4j Aura** làm cơ sở dữ liệu đồ thị và tìm kiếm vector.
3. **Vertical Slice:** Xây dựng luồng chạy dọc nhỏ nhất (end-to-end) trước, sau đó mới nạp RAG vào Neo4j Aura, thêm quản lý phiên (Session), Semantic Cache, và Streaming/TTS. Không tạo sẵn hàng loạt file rỗng ngay từ ngày đầu.

---

## 0. Hiện trạng Workspace & Chiến lược lọc dữ liệu (`fi_ai_mas_llm_dataset`)

Hiện tại thư mục gốc `website_coffee/` đang chứa:
- `fi_ai_mas_llm_dataset/data_pack/` (chứa toàn bộ dữ liệu thô và các file SFT chưa lọc).
- `LLM - multiagent_llm_competency_test.pdf` (tài liệu yêu cầu bài toán).

### Quy tắc di chuyển và lọc dữ liệu (Thực hiện ở Phase 0)
Chúng ta **không xóa** thư mục gốc ngay mà sẽ viết script hoặc copy có chọn lọc sang thư mục `data/` chuẩn của dự án:

1. **Giữ lại & Đưa vào `data/raw/` (Dùng để đẩy lên Neo4j Aura):**
   - `data_pack/data/kb/menu.csv` $\rightarrow$ `data/raw/menu/menu.csv` (120 món ăn/thức uống).
   - `data_pack/data/kb/faq.csv` $\rightarrow$ `data/raw/faq/faq.csv` (160 cặp câu hỏi - trả lời).
   - `data_pack/data/kb/docs/*` ($\text{.docx}$, $\text{.pdf}$) $\rightarrow$ `data/raw/documents/` (Tài liệu chính sách, chi nhánh, quy trình).
   - `data_pack/data/kb/doc_sections_manifest.json` $\rightarrow$ `data/raw/documents/doc_sections_manifest.json` (Các đoạn chunk chuẩn đã chia sẵn).
   - *(Tùy chọn tham khảo)* `data_pack/scripts/common.py`: Chứa nguồn dữ liệu gốc để đối chiếu cấu trúc.

2. **Giữ lại & Đưa vào `data/evaluation/` (Dùng để test & benchmark):**
   - `data_pack/data/eval/rag_eval_20.json` $\rightarrow$ `data/evaluation/rag_eval_20.json` (20 câu hỏi test độ chính xác RAG & chống bịa đặt).
   - `data_pack/data/eval/tts_cases.json` $\rightarrow$ `data/evaluation/tts_cases.json` (Các test case chuẩn hóa số, tiền tệ, đơn vị cho TTS).
   - `data_pack/data/router/router_test.json` $\rightarrow$ `data/evaluation/router_test.json` (Chỉ giữ tập test để đo độ chính xác của Prompt Router qua API).

3. **Bỏ qua (Không sử dụng trong kiến trúc API-First):**
   - `router_train.json`, `router_val.json`, `router_*_sft.jsonl`.
   - `cache/intent_extraction.json`, `intent_extraction_*_sft.jsonl`.

---

## 1. Mục tiêu hệ thống (System Objective)

Hệ thống nhận tin nhắn từ khách hàng trên website, kiểm tra bộ nhớ đệm ngữ nghĩa (Semantic Cache), phân loại vào 1 trong 4 luồng (Routes), gọi Agent chuyên biệt tương ứng, truy xuất tri thức từ **Neo4j Aura** khi cần, sinh câu trả lời và stream về phía Client kèm dữ liệu đọc giọng nói (TTS).

```text
Client (Web UI)
  -> API (FastAPI)
  -> ChatService
  -> Semantic Cache (Redis / Vector lookup)
  -> Router (Jev System One qua OpenRouter Decisions API, typed `choice`)
  -> OrderAgent | ConsultantAgent | FAQAgent | Ignore
  -> Business Service / Graph RAG (Neo4j Aura)
  -> Generator LLM API
  -> SSE / TTS Output
```

4 luồng chính (Primary routes):
- `order`: Tạo hoặc sửa đơn hàng, tra cứu món trong menu, tính tổng tiền chính xác bằng code.
- `consultant`: Tư vấn đồ uống/bánh ngọt dựa trên sở thích, ngân sách, lượng đường/đá, dị ứng.
- `faq`: Trả lời câu hỏi thực tế về quán (giờ mở cửa, chi nhánh, chính sách thú cưng, khuyến mãi) dựa trên FAQ và tài liệu.
- `ignore`: Xử lý các câu nói vô nghĩa, ngoài phạm vi hoặc không thể hành động mà không tốn chi phí gọi các thành phần nặng.

---

## 2. Quy tắc Kiến trúc (Architecture Rules)

### 2.1 Chiều phụ thuộc (Dependency Direction)

Các module chỉ được phép gọi theo một chiều từ trên xuống dưới:

```text
API
  -> Application Services / Orchestrator
    -> Specialized Agents
      -> Domain Services / RAG / Cache
        -> Infrastructure Clients (LLM API, Neo4j Aura, Redis)
```

**Hợp lệ:**
- `chat.py -> ChatService -> DeepAgent -> Router`
- `FAQAgent -> HybridRetriever -> Neo4jRepository -> Neo4jClient`

**Nghiêm cấm:**
- `Neo4jRepository -> FAQAgent`
- `OrderService -> API route`
- `Schema model -> Database client`

### 2.2 Ranh giới trách nhiệm (Responsibility Boundaries)

- **API:** Xác thực dữ liệu đầu vào HTTP, trả về phản hồi JSON hoặc luồng SSE.
- **Orchestrator (`DeepAgent`):** Điều phối luồng đi của request, quản lý lịch sử hội thoại, gọi Cache, Router và chọn Subagent.
- **Agent:** Quyết định cách giải quyết ý định của người dùng (trích xuất tham số, gọi Service/RAG, tạo phản hồi).
- **Service:** Thực thi logic nghiệp vụ tất định (tính tiền, lọc điều kiện cứng, kiểm tra tồn kho/menu).
- **RAG:** Nạp dữ liệu (Ingestion) và truy xuất lai (Vector + Graph Search + Rerank) từ Neo4j Aura.
- **Repository / Client:** Giao tiếp trực tiếp với Neo4j Aura, Redis và nhà cung cấp LLM API.
- **Schema:** Định nghĩa các hợp đồng dữ liệu (Pydantic models) giữa các tầng.
- **Prompt:** Chỉ chứa các hàm/chuỗi xây dựng prompt, tuyệt đối không chứa lệnh gọi mạng.

### 2.3 Ranh giới sử dụng LLM (LLM Boundary)

- **Dùng Jev (TypeSafe System One, qua OpenRouter `POST /api/alpha/decisions`, cùng API key) cho:** Phân loại luồng (Router) bằng câu hỏi `choice`. Jev trả về lựa chọn + xác suất + `confidence`, rẻ và nhanh hơn LLM. Nếu Jev lỗi/timeout hoặc `confidence < ROUTER_CONFIDENCE_THRESHOLD` thì fallback về `ignore`.
- **Dùng LLM API (OpenRouter) cho:** Trích xuất thông tin đặt hàng/ý định (Extraction), trích xuất thực thể tài liệu (Entity Extraction), viết lời tư vấn và sinh câu trả lời tự nhiên.
- **Dùng Code tất định (Deterministic Code) cho:** Tính tổng tiền đơn hàng, áp mã giảm giá, lọc giá tiền $\le$ ngân sách, kiểm tra timeout, retry, ngưỡng tương đồng cache (similarity threshold) và chuyển trạng thái.
- **Bắt buộc:** Mọi đầu ra có cấu trúc từ LLM đều phải được parse và xác thực qua Pydantic Schema trước khi đưa vào logic nghiệp vụ.

---

## 3. Cấu trúc thư mục mục tiêu (Target Repository Skeleton)

*(Đã tinh gọn phần huấn luyện SFT offline để phù hợp với định hướng gọi API và cấu trúc `website_coffee`)*

```text
website_coffee/
├── src/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── chat.py
│   │   │   ├── health.py
│   │   │   └── metrics.py
│   │   ├── dependencies.py
│   │   ├── middleware.py
│   │   ├── streaming.py
│   │   └── __init__.py
│   ├── agent/
│   │   ├── deep_agent.py
│   │   ├── router.py
│   │   ├── llm.py
│   │   ├── history.py
│   │   ├── conversation_summary.py
│   │   ├── session_store.py
│   │   ├── request_queue.py
│   │   ├── subagent_registry.py
│   │   └── __init__.py
│   ├── subagents/
│   │   ├── base.py
│   │   ├── order_agent.py
│   │   ├── consultant_agent.py
│   │   ├── faq_agent.py
│   │   └── __init__.py
│   ├── schema/
│   │   ├── common.py
│   │   ├── router.py
│   │   ├── chat.py
│   │   ├── order.py
│   │   ├── consultant.py
│   │   ├── faq.py
│   │   ├── session.py
│   │   ├── retrieval.py
│   │   ├── cache.py
│   │   └── __init__.py
│   ├── prompt/
│   │   ├── router.py
│   │   ├── order_agent.py
│   │   ├── consultant_agent.py
│   │   ├── faq_agent.py
│   │   ├── intent_extractor.py
│   │   ├── summarizer.py
│   │   └── __init__.py
│   ├── rag/
│   │   ├── retrieval/
│   │   │   ├── base.py
│   │   │   ├── vector_search.py
│   │   │   ├── graph_search.py
│   │   │   ├── hybrid_search.py
│   │   │   ├── reranker.py
│   │   │   └── __init__.py
│   │   ├── ingestion/
│   │   │   ├── base.py
│   │   │   ├── menu.py
│   │   │   ├── faq.py
│   │   │   ├── document.py
│   │   │   ├── chunker.py
│   │   │   ├── entity_extractor.py
│   │   │   ├── entity_deduplicator.py
│   │   │   ├── watcher.py
│   │   │   └── __init__.py
│   │   ├── graph/
│   │   │   ├── client.py
│   │   │   ├── repository.py
│   │   │   ├── queries.py
│   │   │   └── __init__.py
│   │   ├── embeddings.py
│   │   └── __init__.py
│   ├── cache/
│   │   ├── semantic_cache.py
│   │   ├── intent_extractor.py
│   │   ├── cache_repository.py
│   │   ├── invalidation.py
│   │   └── __init__.py
│   ├── services/
│   │   ├── chat_service.py
│   │   ├── order_service.py
│   │   ├── consultant_service.py
│   │   ├── faq_service.py
│   │   ├── tts_service.py
│   │   └── __init__.py
│   ├── infrastructure/
│   │   ├── redis_client.py
│   │   ├── model_client.py
│   │   └── __init__.py
│   ├── guardrails/
│   │   ├── tts_normalizer.py
│   │   ├── rate_limiter.py
│   │   ├── timeout.py
│   │   └── __init__.py
│   ├── observability/
│   │   ├── logging.py
│   │   ├── metrics.py
│   │   ├── tracing.py
│   │   └── __init__.py
│   ├── config.py
│   ├── exceptions.py
│   ├── main.py
│   └── __init__.py
├── evaluation/
│   ├── router/
│   │   └── benchmark_router.py
│   ├── rag/
│   │   └── benchmark_retrieval.py
│   ├── cache/
│   │   └── benchmark_cache.py
│   └── e2e/
│       └── benchmark_pipeline.py
├── scripts/
│   ├── prepare_data.py
│   ├── ingest.py
│   ├── serve.py
│   └── benchmark.py
├── data/
│   ├── raw/
│   │   ├── menu/
│   │   ├── faq/
│   │   └── documents/
│   ├── processed/
│   ├── evaluation/
│   └── inbox/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── fixtures/
├── docker/
│   └── api.Dockerfile
├── docs/
│   ├── architecture.md
│   ├── contracts.md
│   └── benchmark.md
├── fi_ai_mas_llm_dataset/          # Bộ dữ liệu gốc hiện có (giữ nguyên làm nguồn)
├── LLM - multiagent_llm_competency_test.pdf
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Makefile
├── pyproject.toml
└── guide.md                        # File định hướng kiến trúc này
```

---

## 4. Chi tiết trách nhiệm của từng File trong `src/`

### 4.1 Các file cấu hình gốc (Root & Bootstrap)
- **`pyproject.toml`**: Định nghĩa phiên bản Python ($\ge 3.11$), các thư viện runtime (`fastapi`, `uvicorn`, `pydantic`, `pydantic-settings`, `openai`/`google-genai`, `neo4j`, `redis`, `pandas`, `python-docx`, `pypdf`, `watchdog`) và công cụ test (`pytest`, `pytest-asyncio`, `ruff`).
- **`.env.example`**: Mẫu biến môi trường gồm: `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_ROUTER_MODEL`, `LLM_GENERATOR_MODEL`, `EMBEDDING_MODEL`, `NEO4J_URI` (dạng `neo4j+s://...` của Aura), `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `REDIS_URL`, và các cấu hình timeout/threshold.
- **`src/config.py`**: Đọc và kiểm tra kiểu dữ liệu từ `.env` thông qua `pydantic-settings`. Xác thực các giá trị như ngưỡng tương đồng cache nằm trong đoạn $[0, 1]$, số chiều vector (`VECTOR_DIMENSIONS`, ví dụ $1536$ hoặc $768$), timeout $> 0$.
- **`src/exceptions.py`**: Định nghĩa các lỗi nghiệp vụ như `RouterOutputError`, `AgentExecutionError`, `RetrievalError`, `QueueTimeoutError`, `ModelServiceUnavailableError`.
- **`src/main.py`**: Khởi tạo ứng dụng FastAPI, gắn middleware, đăng ký routes và quản lý vòng đời (lifespan) để đóng/mở kết nối Neo4j Aura, Redis và HTTP Client an toàn.

### 4.2 Tầng API (`src/api/`)
- **`routes/chat.py`**: Nhận `ChatRequest`, gọi `ChatService` để trả về kết quả JSON hoặc luồng SSE (`StreamingResponse`). Không gọi trực tiếp Neo4j hay Agent.
- **`routes/health.py`**: Kiểm tra trạng thái sống của server (`/health/live`) và trạng thái kết nối tới Neo4j Aura, Redis, LLM API (`/health/ready`).
- **`routes/metrics.py`**: Xuất các chỉ số đo lường hệ thống.
- **`dependencies.py`**: Nơi khởi tạo và tiêm (Dependency Injection) các instance dùng chung (Singleton cho `Neo4jClient`, `RedisClient`, `ModelClient`, `DeepAgent`). Tránh tạo lại kết nối database ở mỗi request.
- **`streaming.py`**: Chuyển đổi các sự kiện token/câu (clause) nội bộ thành chuẩn Server-Sent Events (SSE) gửi về trình duyệt, kết thúc bằng tín hiệu `[DONE]`.

### 4.3 Tầng Hợp đồng dữ liệu (`src/schema/`)
- **`common.py`**: Các Enum dùng chung (`AgentType`, `MessageRole`, `Language`, `SourceReference`).
- **`router.py`**: Định nghĩa `RouterAction` (`order`, `consultant`, `faq`, `ignore`) và `RouterDecision` (chứa `action`, `confidence`, `reasoning` ngắn gọn).
- **`order.py`**: Định nghĩa món hàng được trích xuất (`OrderItemInput`), kết quả khớp menu (`MenuMatch`), giỏ hàng và tổng tiền (`OrderCalculation` sử dụng `int` cho VNĐ hoặc `Decimal`, tuyệt đối không dùng `float`).
- **`consultant.py` & `faq.py`**: Định nghĩa bộ lọc tư vấn (ngân sách, sở thích, dị ứng) và cấu trúc câu trả lời có trích dẫn nguồn (`grounded_sources`).
- **`retrieval.py` & `cache.py` & `session.py`**: Định nghĩa dữ liệu đầu ra của tìm kiếm Neo4j, khóa/ý định của Semantic Cache (`subject`, `action`, `context`) và trạng thái phiên trò chuyện.

### 4.4 Tầng Prompt (`src/prompt/`)
- Chỉ chứa các hàm tạo System Prompt và Few-shot Examples cho `router.py`, `order_agent.py`, `consultant_agent.py`, `faq_agent.py`, `intent_extractor.py`, và `summarizer.py`.

### 4.5 Tầng Điều phối & Agent (`src/agent/` & `src/subagents/`)
- **`infrastructure/model_client.py`**: Lớp bọc (wrapper) giao tiếp với LLM API (OpenAI/Gemini). Hỗ trợ 3 chế độ: sinh văn bản thường, ép kiểu cấu trúc JSON/Pydantic (`generate_structured`), và sinh luồng (`stream_chat`), kèm cơ chế retry và timeout.
- **`agent/router.py`**: Gọi `model_client.generate_structured()` với `RouterDecision` schema. Nếu API lỗi hoặc timeout, trả về fallback an toàn.
- **`agent/deep_agent.py`**: Nhạc trưởng của hệ thống:
  `Tải Session -> Lưu tin nhắn User -> Kiểm tra Semantic Cache -> Gọi Router -> Chọn Subagent từ Registry -> Thực thi Subagent -> Lưu phản hồi Assistant -> Ghi Cache (nếu phù hợp) -> Trả kết quả/Stream`.
- **`subagents/order_agent.py`**: Dùng LLM trích xuất thao tác (thêm/bớt/xác nhận món, số lượng, size) $\rightarrow$ Tra cứu món trong Neo4j $\rightarrow$ Giao cho `OrderService` tính toán số học $\rightarrow$ Dùng LLM viết câu phản hồi xác nhận giỏ hàng.
- **`subagents/consultant_agent.py`**: Dùng LLM trích xuất nhu cầu (ví dụ: ít ngọt, không cafein, dưới $50000\text{ VNĐ}$) $\rightarrow$ Gọi `HybridSearch` và `ConsultantService` để lọc danh sách món thỏa mãn $\rightarrow$ Dùng LLM giới thiệu các món đó.
- **`subagents/faq_agent.py`**: Gọi `HybridSearch` lấy các `Chunk` từ FAQ và tài liệu $\rightarrow$ Kiểm tra ngưỡng bằng chứng (nếu không có thông tin trong dữ liệu, trả lời từ chối khéo léo, cam kết **Zero Hallucination**).

### 4.6 Tầng Graph RAG với Neo4j Aura (`src/rag/`)
- **`graph/client.py`**: Quản lý kết nối `AsyncGraphDatabase.driver` tới Neo4j Aura (`neo4j+s://...`).
- **`graph/queries.py`**: Chứa toàn bộ các câu lệnh Cypher đã tham số hóa:
  - Tạo ràng buộc duy nhất (Uniqueness Constraints) cho `MenuItem`, `Chunk`, `Entity`.
  - Tạo Vector Index (`menu_vector_index`, `chunk_vector_index`).
  - Lệnh `MERGE` nạp dữ liệu và các mối quan hệ `BELONGS_TO`, `NEXT`, `MENTIONS`.
  - Lệnh truy vấn Vector Search kết hợp duyệt đồ thị (Graph Traversal).
- **`embeddings.py`**: Gọi API Embedding để biến văn bản thành mảng vector chuẩn hóa.
- **`ingestion/`**:
  - `menu.py`: Đọc `data/raw/menu/menu.csv`, tạo văn bản mô tả tổng hợp cho mỗi món, gọi API lấy embedding và đẩy lên Neo4j thành nút `MenuItem` nối với `Category`.
  - `faq.py`: Đọc `data/raw/faq/faq.csv`, tạo nút `Chunk` (source=`faq`) kèm vector embedding.
  - `document.py` & `chunker.py` & `entity_extractor.py` & `entity_deduplicator.py`: Đọc `doc_sections_manifest.json` (hoặc parse từ file `.docx`/`.pdf`), tạo chuỗi nút `Chunk` liên kết qua quan hệ `[:NEXT]`, trích xuất `Entity` (hợp nhất các thực thể trùng lặp bằng độ tương đồng Jaccard $\ge \text{threshold}$) và nối qua quan hệ `[:MENTIONS]`.
  - `watcher.py`: Theo dõi thư mục `data/inbox/` để tự động nạp các file tài liệu/menu mới thêm vào mà không cần khởi động lại hệ thống.
- **`retrieval/`**:
  - `vector_search.py`: Tìm kiếm top-$k$ `MenuItem` hoặc `Chunk` bằng Vector Index trên Neo4j Aura.
  - `graph_search.py`: Mở rộng ngữ cảnh bằng cách lấy các `Chunk` liền kề (`[:NEXT]`) và các `Chunk` cùng nhắc tới một `Entity` (`[:MENTIONS]`).
  - `reranker.py` & `hybrid_search.py`: Gộp kết quả Vector + Graph, loại bỏ trùng lặp, chấm điểm lại (rerank) và cắt theo ngưỡng trước khi đưa vào Agent.

### 4.7 Tầng Semantic Cache, Guardrails & Services
- **`cache/`**: Dùng LLM API trích xuất bộ ba `(subject, action, context)`. Chỉ lưu và khớp cache cho các câu hỏi tĩnh (FAQ, thông tin chung) khi độ tương đồng cosine của `action` vượt ngưỡng (ví dụ $\ge 0.90$) và khớp `subject`. Tự động xóa cache (`invalidation.py`) khi dữ liệu menu/tài liệu thay đổi.
- **`guardrails/tts_normalizer.py`**: Chuyển đổi các ký hiệu tiền tệ, viết tắt, số lượng (ví dụ: `45k`, `50.000đ`, `size M`, `100%`) thành chữ tiếng Việt đọc tự nhiên trước khi đưa vào `tts_service.py` (đối chiếu với bộ test `tts_cases.json`).

---

## 5. Lộ trình triển khai từng bước (Implementation Phases)

Hãy thực hiện tuần tự từng Phase. Trên Antigravity IDE, bạn có thể yêu cầu AI Agent hoàn thành từng Phase một và chạy kiểm thử trước khi sang Phase tiếp theo.

### Phase 0: Khởi tạo Repository & Lọc dữ liệu (`prepare_data`)
**Mục tiêu:** Tạo bộ khung dự án chạy được, cấu hình kết nối `.env` và lọc dữ liệu từ `fi_ai_mas_llm_dataset` sang thư mục `data/`.
**Thứ tự tạo file:**
1. `pyproject.toml`
2. `.gitignore`
3. `.env.example` (và tạo file `.env` thực tế chứa thông tin Neo4j Aura + LLM API Key)
4. `src/__init__.py`, `src/config.py`, `src/exceptions.py`, `src/main.py`
5. `scripts/prepare_data.py` (Script tự động copy `menu.csv`, `faq.csv`, `docs/*`, `doc_sections_manifest.json`, `rag_eval_20.json`, `tts_cases.json`, `router_test.json` từ `fi_ai_mas_llm_dataset/data_pack` vào đúng cấu trúc `data/`)
6. `tests/unit/test_config.py`
**Tiêu chí hoàn thành:** Chạy `python scripts/prepare_data.py` thấy dữ liệu nằm gọn trong `data/raw/` và `data/evaluation/`. Chạy `pytest` pass.

---

### Phase 1: Hợp đồng dữ liệu (Schemas) & API Router
**Mục tiêu:** Nhận 1 câu chat bất kỳ và phân loại chính xác vào 4 luồng (`order`, `consultant`, `faq`, `ignore`) qua Jev (OpenRouter Decisions API).
**Thứ tự tạo file:**
1. `src/schema/__init__.py`, `src/schema/common.py`, `src/schema/router.py`, `src/schema/chat.py`
2. `src/prompt/__init__.py`, `src/prompt/router.py`
3. `src/infrastructure/__init__.py`, `src/infrastructure/model_client.py`
4. `src/agent/__init__.py`, `src/agent/router.py`
5. `tests/unit/agent/test_router.py`
6. `evaluation/router/benchmark_router.py` (Chạy thử trên tập `data/evaluation/router_test.json`)
**Tiêu chí hoàn thành:** Router trả về đúng Pydantic schema `RouterDecision`, xử lý được lỗi mạng/timeout và đạt độ chính xác cao trên tập `router_test.json`.

---

### Phase 2: Luồng API & Orchestrator tối thiểu (Vertical Slice đầu tiên)
**Mục tiêu:** Kết nối từ FastAPI endpoint $\rightarrow$ `ChatService` $\rightarrow$ `DeepAgent` $\rightarrow$ `Router` $\rightarrow$ các Subagent giả lập (Stub).
**Thứ tự tạo file:**
1. `src/subagents/__init__.py`, `src/subagents/base.py`
2. `src/schema/order.py`, `src/schema/consultant.py`, `src/schema/faq.py`
3. `src/agent/subagent_registry.py`, `src/agent/deep_agent.py`
4. `src/services/__init__.py`, `src/services/chat_service.py`
5. `src/api/__init__.py`, `src/api/routes/chat.py`, `src/api/dependencies.py`
6. Cập nhật `src/main.py` để gắn route `/api/v1/chat`.
7. `tests/unit/agent/test_deep_agent.py`
**Tiêu chí hoàn thành:** Gửi POST request tới `/api/v1/chat` nhận về phản hồi đúng luồng từ hệ thống.

---

### Phase 3: Kết nối Neo4j Aura & Nạp dữ liệu Menu (Menu Ingestion)
**Mục tiêu:** Kết nối thành công với instance **Neo4j Aura** bạn đã tạo và đẩy toàn bộ 120 món từ `menu.csv` kèm Vector Embedding lên đám mây.
**Thứ tự tạo file:**
1. `src/rag/__init__.py`, `src/rag/graph/__init__.py`
2. `src/rag/graph/client.py`, `src/rag/graph/queries.py`
3. `src/schema/retrieval.py`, `src/rag/graph/repository.py`
4. `src/rag/embeddings.py`
5. `src/rag/ingestion/__init__.py`, `src/rag/ingestion/base.py`, `src/rag/ingestion/menu.py`
6. `scripts/ingest.py` (Hỗ trợ cờ `--target menu`)
7. `tests/integration/test_neo4j_repository.py`
**Tiêu chí hoàn thành:** Chạy `python scripts/ingest.py --target menu` đẩy đủ 120 nút `MenuItem` và Vector Index lên Neo4j Aura. Kiểm tra trên giao diện Neo4j Aura thấy các Node và Relationship hiển thị.

---

### Phase 4: Hoàn thiện Order Agent (Luồng đặt hàng)
**Mục tiêu:** Khách hàng có thể gọi món, đổi size, thêm/bớt số lượng; hệ thống tra cứu giá thật từ Neo4j Aura và tính tổng tiền bằng code Python.
**Thứ tự tạo file:**
1. `src/prompt/order_agent.py`
2. `src/services/order_service.py`
3. `src/subagents/order_agent.py`
4. Đăng ký `OrderAgent` vào `src/agent/subagent_registry.py`
5. `tests/unit/services/test_order_service.py`, `tests/e2e/test_order_flow.py`
**Tiêu chí hoàn thành:** LLM không bao giờ tự cộng tiền; mọi phép tính tổng tiền, kiểm tra món không tồn tại hoặc số lượng âm đều do `OrderService` kiểm soát chặt chẽ.

---

### Phase 5: Nạp dữ liệu FAQ, Tài liệu & Watch Mode lên Neo4j Aura
**Mục tiêu:** Đẩy `faq.csv`, `doc_sections_manifest.json` và các tài liệu chính sách lên Neo4j Aura với đầy đủ các nút `Chunk`, `Entity` và quan hệ `[:NEXT]`, `[:MENTIONS]`.
**Thứ tự tạo file:**
1. `src/rag/ingestion/chunker.py`, `src/rag/ingestion/faq.py`
2. `src/rag/ingestion/entity_extractor.py`, `src/rag/ingestion/entity_deduplicator.py`
3. `src/rag/ingestion/document.py`, `src/rag/ingestion/watcher.py`
4. Mở rộng `queries.py`, `repository.py` và `scripts/ingest.py` (`--target faq`, `--target docs`, `--target all`)
5. `tests/unit/rag/test_entity_deduplicator.py`, `tests/integration/test_faq_ingestion.py`
**Tiêu chí hoàn thành:** Chạy `python scripts/ingest.py --target all` nạp toàn bộ cơ sở tri thức lên Neo4j Aura mà không bị trùng lặp bản ghi khi chạy lại (idempotent).

---

### Phase 6: Hybrid Graph RAG (Vector + Graph Expansion + Reranker)
**Mục tiêu:** Xây dựng bộ truy xuất kết hợp tìm kiếm ngữ nghĩa Vector và mở rộng đồ thị trên Neo4j Aura.
**Thứ tự tạo file:**
1. `src/rag/retrieval/__init__.py`, `src/rag/retrieval/base.py`
2. `src/rag/retrieval/vector_search.py`, `src/rag/retrieval/graph_search.py`
3. `src/rag/retrieval/reranker.py`, `src/rag/retrieval/hybrid_search.py`
4. `evaluation/rag/benchmark_retrieval.py` (Đánh giá trên `data/evaluation/rag_eval_20.json`)
**Tiêu chí hoàn thành:** Truy xuất trả về đúng ngữ cảnh cho 20 câu hỏi trong `rag_eval_20.json`, chứng minh được việc mở rộng qua đồ thị (`[:NEXT]`, `[:MENTIONS]`) mang lại ngữ cảnh đầy đủ hơn chỉ dùng Vector đơn thuần.

---

### Phase 7: Hoàn thiện FAQ Agent & Consultant Agent
**Mục tiêu:** Hoàn tất cả 3 Subagent chuyên biệt sử dụng chung nền tảng Hybrid Graph RAG.
**Thứ tự tạo file:**
1. `src/prompt/faq_agent.py`, `src/services/faq_service.py`, `src/subagents/faq_agent.py`
2. `src/prompt/consultant_agent.py`, `src/services/consultant_service.py`, `src/subagents/consultant_agent.py`
3. Đăng ký cả 2 Agent vào `src/agent/subagent_registry.py`
4. `tests/e2e/test_faq_flow.py`, `tests/e2e/test_consultant_flow.py`
**Tiêu chí hoàn thành:**
- `FAQAgent` trả lời chính xác câu hỏi có trong tài liệu kèm trích dẫn nguồn, và từ chối trả lời các câu hỏi ngoài luồng (như hỏi công thức bí mật, thông tin đối thủ) đúng theo tiêu chuẩn Zero Hallucination.
- `ConsultantAgent` lọc đúng món theo giá tiền, dị ứng, lượng cafein trước khi sinh lời tư vấn.

---

### Phase 8: Quản lý Phiên (Session), Tóm tắt hội thoại & Hàng đợi (Concurrency)
**Mục tiêu:** Hỗ trợ hội thoại nhiều lượt (multi-turn) và chịu tải đồng thời an toàn.
**Thứ tự tạo file:**
1. `src/schema/session.py`, `src/infrastructure/redis_client.py` (Có hỗ trợ In-Memory fallback nếu chạy local chưa bật Redis)
2. `src/agent/session_store.py`, `src/agent/history.py`
3. `src/prompt/summarizer.py`, `src/agent/conversation_summary.py`
4. `src/guardrails/__init__.py`, `src/guardrails/timeout.py`, `src/agent/request_queue.py`
5. Tích hợp vào `ChatService` và `DeepAgent`.
**Tiêu chí hoàn thành:** Khách hàng có thể nói *"Cho mình 2 ly như vừa tư vấn nhé"* ở lượt chat tiếp theo và hệ thống hiểu đúng ngữ cảnh.

---

### Phase 9: SSE Streaming & Chuẩn hóa giọng đọc (TTS Normalizer)
**Mục tiêu:** Stream câu trả lời theo thời gian thực và chuẩn hóa văn bản tiếng Việt cho bộ đọc TTS.
**Thứ tự tạo file:**
1. `src/guardrails/tts_normalizer.py`
2. `src/services/tts_service.py`
3. `src/api/streaming.py` và cập nhật `src/api/routes/chat.py`
4. `tests/unit/guardrails/test_tts_normalizer.py` (Kiểm thử trực tiếp với toàn bộ test case trong `data/evaluation/tts_cases.json`)
**Tiêu chí hoàn thành:** Vượt qua 100% các trường hợp chuẩn hóa tiền tệ, đơn vị, viết tắt trong `tts_cases.json` và stream mượt mà qua SSE.

---

### Phase 10: Semantic Cache, Guardrails & Observability
**Mục tiêu:** Tăng tốc độ phản hồi và giảm chi phí gọi API bằng Semantic Cache dựa trên trích xuất ý định (`subject`, `action`, `context`).
**Thứ tự tạo file:**
1. `src/schema/cache.py`, `src/prompt/intent_extractor.py`
2. `src/cache/__init__.py`, `src/cache/intent_extractor.py`, `src/cache/cache_repository.py`, `src/cache/semantic_cache.py`, `src/cache/invalidation.py`
3. `src/observability/logging.py`, `src/observability/metrics.py`, `src/observability/tracing.py`
4. `src/guardrails/rate_limiter.py`, `src/api/middleware.py`, `src/api/routes/health.py`, `src/api/routes/metrics.py`
5. `evaluation/cache/benchmark_cache.py`, `evaluation/e2e/benchmark_pipeline.py`

---

## 6. Lát cắt dọc đầu tiên (Recommended First Vertical Slice)

Khi bắt đầu gõ lệnh cho Agent trên Antigravity IDE (`Ctrl + L`), **đừng yêu cầu tạo tất cả các file cùng lúc**. Hãy yêu cầu Agent thực hiện **Phase 0 + Phase 1 + Phase 2** trước với danh sách file tối thiểu sau:

```text
scripts/
└── prepare_data.py
src/
├── main.py
├── config.py
├── exceptions.py
├── schema/
│   ├── common.py
│   ├── router.py
│   └── chat.py
├── prompt/
│   └── router.py
├── infrastructure/
│   └── model_client.py
├── agent/
│   ├── router.py
│   ├── subagent_registry.py
│   └── deep_agent.py
├── subagents/
│   └── base.py
├── services/
│   └── chat_service.py
└── api/
    ├── dependencies.py
    └── routes/chat.py
```

Ngay sau khi lát cắt này chạy thông suốt, chuyển sang **Phase 3** để nạp dữ liệu lên **Neo4j Aura**.

---

## 7. Checklist theo dõi tiến độ (Phase Tracking Checklist)

```text
[x] Phase 0: Khởi tạo Repository & Lọc dữ liệu từ fi_ai_mas_llm_dataset
[x] Phase 1: Core Schemas & Jev Router (OpenRouter Decisions API) — baseline 87.8% trên router_test.json
[ ] Phase 2: Minimal API & Orchestrator Vertical Slice
[ ] Phase 3: Kết nối Neo4j Aura & Nạp dữ liệu Menu (menu.csv)
[ ] Phase 4: Hoàn thiện Order Agent (Logic tính tiền tất định + Tra cứu Neo4j)
[ ] Phase 5: Nạp dữ liệu FAQ, Documents & Watch Mode lên Neo4j Aura
[ ] Phase 6: Hybrid Graph RAG (Vector Search + Graph Traversal + Reranker)
[ ] Phase 7: Hoàn thiện FAQ Agent & Consultant Agent
[ ] Phase 8: Quản lý Session, Tóm tắt hội thoại & Request Queue
[ ] Phase 9: SSE Streaming & Bộ chuẩn hóa TTS (tts_cases.json)
[ ] Phase 10: Semantic Cache, Observability & E2E Benchmark
```