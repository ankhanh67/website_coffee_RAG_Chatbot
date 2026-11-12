# Bộ dữ liệu cho bài kiểm tra MAS-LLM-2026-FINAL

Dữ liệu **mô phỏng** cho robot tư vấn F&B (Highlands Coffee). Menu, giá, chi nhánh, wifi, chính sách đều là dữ liệu giả lập, **không phải thông tin thật** của Highlands. Mọi file dùng chung một nguồn sự thật (`scripts/common.py`), nên giá, giờ mở cửa và chính sách khớp nhau giữa menu, FAQ, tài liệu và cache.

## Cấu trúc

```
data/
  router/    router_train.json, router_test.json, router_*_sft.jsonl        -> A1
  kb/        menu.csv, faq.csv, docs/*.docx|pdf, doc_sections_manifest.json  -> B1, A2
  cache/     intent_extraction.json (+ *_sft.jsonl), cache_seed.json,
             cache_invalidation_map.json, cache_eval_500.json               -> C2
  eval/      rag_eval_20.json, tts_cases.json                               -> B1, C3
scripts/     generator + validate.py + gen_router_data.py (pipeline API) + tts_preprocess.py
```

## Từng bộ dữ liệu

| File | Số lượng | Ghi chú |
|---|---|---|
| `router_train.json` | 4.000 | 1.000/intent, 12% hard samples, vi/en/vi-en |
| `router_test.json` | 400 | 100/intent, 20% hard. **Template không xuất hiện ở train**, không trùng câu nào |
| `router_*_sft.jsonl` | 4.000 / 400 | Định dạng chat `messages`, assistant trả `{"action": "<intent>"}` |
| `menu.csv` | 120 món | 10 nhóm, giá S/M/L, caffeine, thuần chay, dị ứng, nguyên liệu, mô tả vi/en |
| `faq.csv` | 160 dòng | 40 chủ đề × 4 cách hỏi (2 vi, 2 en), cột `topic_id` để nhóm |
| `docs/` | 4 file, 62 section | 2 docx (chính sách, khuyến mãi) + 2 pdf (quy trình, chi nhánh) |
| `doc_sections_manifest.json` | 62 | Mỗi section là một đoạn ngữ nghĩa, dùng làm ground truth cho RAG |
| `intent_extraction.json` | 1.500 | 1.200 train / 150 val / 150 test, tách `subject` / `action` / `context` |
| `cache_seed.json` | 30 nhóm | Response template vi/en, mở đầu/kết thúc/đuôi context để paraphrase |
| `cache_eval_500.json` | 500 | 425 nên hit, 75 nên miss, 448 câu có context |
| `rag_eval_20.json` | 20 | 6 menu, 5 faq, 5 tài liệu, 2 multi-chunk, 2 không trả lời được |
| `tts_cases.json` | 44 | Input + expected viết tay, hàm tham chiếu `tts_preprocess.py` đạt 100% |

## Schema chính

**Router** (`router_*.json`): `id, text, label (0-3), intent, is_noise, language ("vi"|"en"|"vi-en"), is_hard`.
Nhãn: `0=order, 1=consultant, 2=faq, 3=ignore`. `is_noise = true` khi intent là `ignore`. Một phần mẫu có lỗi chính tả hoặc bỏ dấu để giống đầu ra ASR.

**Quy tắc gán nhãn cho hard samples** (đề không nêu, tôi tự đặt, bạn có thể đổi):
1. Có lệnh mua/trả tiền rõ ràng kèm câu hỏi phụ → `order` ("Cho anh 1 phin sữa đá, có ngọt không em?").
2. Nhờ quán chọn hộ, hỏi giá/vị/thành phần món cụ thể → `consultant` ("Có gì ngon rẻ không?", "Cho anh món nào ngon nhất đi").
3. Hỏi thông tin chung của quán, chính sách, dịch vụ → `faq`, kể cả khi nhắc tên món ("Trà đào có giao tận nơi không?").
4. Chào + yêu cầu thật → nhãn của yêu cầu ("Hello, wifi tên gì vậy?" → `faq`). Chào, ậm ừ, câu bỏ dở không có yêu cầu → `ignore`.

**Intent extraction**: `text, subject, action, context, cache_key (= action), action_group, route, split, language`. `subject`, `action`, `context` luôn là chuỗi con của `text` (đã kiểm tra). `subject` rỗng khi câu không có chủ ngữ (~16%), `context` rỗng ở ~10%. Split val/test dùng thêm cách nói và khung câu mà train không có, để đo khả năng tổng quát hóa.

**Cache**: `cache_eval_500.json` giả định cache đã nạp sẵn 30 nhóm trong `cache_seed.json`. `expected_hit=false` là 75 yêu cầu ngoài phạm vi (đặt tiệc cưới, xin việc...). Hit rate = số câu hit đúng nhóm / 500, ngưỡng đề là ≥ 60%. `cache_invalidation_map.json` cho biết nguồn nào thay đổi (menu, faq, doc) thì xóa nhóm cache nào.

**RAG eval**: mỗi câu có `gold_menu_ids`, `gold_faq_ids`, `gold_doc_sections`, `answer_keywords`, `forbidden_keywords`. Q17 và Q18 có `needs_graph_expansion=true` vì đáp án nằm ở 2 chunk liền kề (đo mức tăng recall của Graph Expansion). Q19 và Q20 hỏi thứ không có trong dữ liệu, mô hình phải nói không có thông tin (đo zero hallucination).

## Dùng nhanh

```bash
# Fine-tune Router: dùng router_train_sft.jsonl, đánh giá trên router_test.json
# Nạp Graph DB:    menu.csv, faq.csv, docs/* (manifest cho biết ranh giới section)
# Kiểm tra lại:    python scripts/validate.py       (44 kiểm tra)
# Sinh lại tất cả: bash scripts/run_all.sh
```

Pipeline sinh dữ liệu bằng API cho yêu cầu A1.2:

```bash
export LLM_BASE_URL=http://localhost:8000/v1 LLM_API_KEY=xxx LLM_MODEL=qwen2.5-7b-instruct
python scripts/gen_router_data.py --per-intent 1100 --concurrency 8   # tự resume nếu bị ngắt
python scripts/gen_router_data.py --mock --per-intent 60              # thử pipeline không cần API
```

## Hạn chế cần biết

- **Router và intent extraction sinh bằng template**, không phải LLM. Câu có đa dạng bề mặt (xưng hô, món, lỗi chính tả, từ đệm) nhưng ít đa dạng cấu trúc hơn dữ liệu do LLM viết. Baseline TF-IDF đơn giản đạt 92,8% trên test (82,5% trên hard samples) nên nhãn học được và không bị rò rỉ, nhưng đừng coi con số đó là trần của bài toán. Nên trộn thêm dữ liệu từ `gen_router_data.py` để model chịu được câu thật.
- **`gen_router_data.py` mới chỉ được test với LLM giả lập** (`--mock`): async, dedup, checkpoint/resume (kể cả dòng cuối bị cắt khi crash), retry với backoff đều đã chạy đúng. Chưa gọi thử API thật, nên prompt có thể cần chỉnh sau lần chạy đầu.
- Tài liệu nội bộ chỉ có tiếng Việt, FAQ có cả vi và en. Chưa có ngôn ngữ thứ ba.
- Menu và FAQ có đủ số lượng tối thiểu của đề (≥100 món, ≥150 FAQ, ≥50 chunk tài liệu), không nhiều hơn nhiều. Nếu muốn kiểm tra recall ở quy mô lớn hơn thì cần thêm dữ liệu.
- Context của intent extraction đôi khi ghép ngẫu nhiên nên có câu hơi gượng ("mua thẻ quà tặng cho 12 người tại chi nhánh Cầu Giấy cho con gái 5 tuổi"). Chấp nhận được cho huấn luyện tách span, nhưng không phải hội thoại tự nhiên.
