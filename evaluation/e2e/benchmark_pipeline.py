"""Full E2E multi-agent pipeline benchmark across Order, Consultant, FAQ, and Semantic Cache."""

import asyncio
import time
from typing import Any

from src.api.dependencies import get_chat_service, get_semantic_cache
from src.observability.metrics import metrics_collector
from src.schema.chat import ChatRequest
from src.schema.router import RouterAction

BENCHMARK_CASES = [
    # 1. Consultant: Menu & Diet inquiries
    {
        "id": "consultant-1",
        "message": "Quán có đồ uống nào không có caffeine và thuần chay không?",
        "expected_action": RouterAction.CONSULTANT,
        "keywords": ["trà", "caffeine"],
    },
    {
        "id": "consultant-2",
        "message": "Quán có những loại cà phê nào?",
        "expected_action": RouterAction.CONSULTANT,
        "keywords": ["cà phê", "phindi"],
    },
    # 2. FAQ: Policies & Amenities
    {
        "id": "faq-1",
        "message": "Chi nhánh Hà Nội nào có chỗ đỗ ô tô?",
        "expected_action": RouterAction.FAQ,
        "keywords": ["ô tô", "chi nhánh"],
    },
    {
        "id": "faq-2",
        "message": "Quán mở cửa từ mấy giờ đến mấy giờ?",
        "expected_action": RouterAction.FAQ,
        "keywords": ["giờ", "mở cửa"],
    },
    # 3. Order: Cart creation & Deterministic calculation
    {
        "id": "order-1",
        "message": "Cho mình đặt 2 ly Trà Đào Cam Sả size L và 1 bánh Tiramisu",
        "expected_action": RouterAction.ORDER,
        "keywords": ["đơn", "giá"],
    },
    # 4. Ignore: Chitchat outside coffee shop scope
    {
        "id": "ignore-1",
        "message": "Thời tiết hôm nay thế nào?",
        "expected_action": RouterAction.IGNORE,
        "keywords": ["hỗ trợ", "quán"],
    },
]


async def run_pipeline_benchmark() -> dict[str, Any]:
    chat_service = get_chat_service()
    cache = get_semantic_cache()
    metrics_collector.reset()

    results = []
    print("\n" + "=" * 60)
    print("🚀 RUNNING MULTI-AGENT E2E BENCHMARK PIPELINE")
    print("=" * 60)

    # Round 1: Cold start test across all cases
    correct_actions = 0
    t_start = time.perf_counter()

    for i, case in enumerate(BENCHMARK_CASES, start=1):
        sess_id = f"bench-cold-{case['id']}"
        req = ChatRequest(session_id=sess_id, message=case["message"])

        t0 = time.perf_counter()
        resp = await chat_service.chat(req)
        lat_ms = round((time.perf_counter() - t0) * 1000, 1)

        action_ok = resp.action == case["expected_action"]
        if action_ok:
            correct_actions += 1

        print(
            f"[{i}/{len(BENCHMARK_CASES)}] {case['id']:<15} | Action: {resp.action.value:<10} "
            f"| Expected: {case['expected_action'].value:<10} | Latency: {lat_ms:>6.1f}ms | {'✅ PASS' if action_ok else '❌ FAIL'}"
        )

        results.append({
            "id": case["id"],
            "message": case["message"],
            "expected_action": case["expected_action"].value,
            "actual_action": resp.action.value,
            "latency_ms": lat_ms,
            "passed": action_ok,
            "reply_preview": resp.reply[:80].replace("\n", " "),
        })

    # Round 2: Semantic Cache speedup test
    print("\n" + "-" * 60)
    print("⚡ TESTING SEMANTIC CACHE SPEEDUP (WARM QUERIES)")
    print("-" * 60)

    cache_cases = [
        ("Quán có những loại cà phê nào?", "exact"),
        ("quán có các loại cà phê nào ạ?", "semantic"),
    ]

    cache_hits = 0
    for query, test_type in cache_cases:
        t0 = time.perf_counter()
        cached = await cache.lookup(query)
        lat_ms = round((time.perf_counter() - t0) * 1000, 2)
        is_hit = cached is not None
        if is_hit:
            cache_hits += 1
        print(f"  [{test_type.upper():<8}] '{query}' -> Latency: {lat_ms:>5.2f}ms | {'⚡ HIT' if is_hit else '⚠️ MISS'}")

    total_time = round(time.perf_counter() - t_start, 2)
    accuracy = round(correct_actions / len(BENCHMARK_CASES) * 100, 1)

    print("\n" + "=" * 60)
    print(f"📊 SUMMARY: Accuracy: {accuracy}% ({correct_actions}/{len(BENCHMARK_CASES)}) | Total Time: {total_time}s")
    print(f"🎯 Cache Hits: {cache_hits}/{len(cache_cases)}")
    print("=" * 60 + "\n")

    return {
        "accuracy_pct": accuracy,
        "total_cases": len(BENCHMARK_CASES),
        "passed_cases": correct_actions,
        "cache_hits": cache_hits,
        "total_time_seconds": total_time,
        "results": results,
    }


if __name__ == "__main__":
    asyncio.run(run_pipeline_benchmark())
