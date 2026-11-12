"""Benchmark the Jev router on data/evaluation/router_test.json.

Usage: uv run python -m evaluation.router.benchmark_router [--limit N] [--concurrency 10]
"""

import argparse
import asyncio
import json
import time
from collections import defaultdict
from pathlib import Path

from src.agent.router import Router
from src.config import get_settings
from src.infrastructure.model_client import ModelClient

DATA = Path(__file__).resolve().parents[2] / "data" / "evaluation" / "router_test.json"


class CostTrackingClient(ModelClient):
    total_cost = 0.0

    async def decide(self, model, state, questions):
        raw = await super().decide(model, state, questions)
        self.total_cost += raw.get("usage", {}).get("cost", 0.0)
        return raw


async def run(limit: int | None, concurrency: int) -> None:
    s = get_settings()
    cases = json.loads(DATA.read_text(encoding="utf-8"))[:limit]
    client = CostTrackingClient(
        api_key=s.llm_api_key.get_secret_value(),
        decisions_url=s.llm_decisions_url,
        timeout_seconds=s.llm_timeout_seconds,
        max_retries=s.llm_max_retries,
    )
    router = Router(client, s.llm_router_model, s.router_confidence_threshold)
    sem = asyncio.Semaphore(concurrency)

    async def one(case):
        async with sem:
            t0 = time.perf_counter()
            d = await router.route(case["text"])
            return case, d, time.perf_counter() - t0

    t_start = time.perf_counter()
    results = await asyncio.gather(*(one(c) for c in cases))
    wall = time.perf_counter() - t_start
    await client.aclose()

    groups: dict[str, list[bool]] = defaultdict(list)
    errors = []
    for case, d, _ in results:
        ok = d.action.value == case["intent"]
        keys = ["all", f"intent={case['intent']}", f"lang={case['language']}",
                f"hard={case['is_hard']}", f"noise={case['is_noise']}"]
        for k in keys:
            groups[k].append(ok)
        if not ok:
            errors.append((case, d))

    latencies = sorted(lat for _, _, lat in results)
    fallbacks = sum(d.is_fallback for _, d, _ in results)
    print(f"Model: {s.llm_router_model}  threshold={s.router_confidence_threshold}")
    for k in sorted(groups, key=lambda k: (k != "all", k)):
        v = groups[k]
        print(f"  {k:<22} {sum(v):>4}/{len(v):<4} = {sum(v) / len(v):.1%}")
    print(f"Fallbacks: {fallbacks}  |  latency p50={latencies[len(latencies) // 2]:.2f}s "
          f"p95={latencies[int(len(latencies) * 0.95) - 1]:.2f}s  |  wall={wall:.1f}s  "
          f"|  cost=${client.total_cost:.5f}")
    print("\nSample errors:")
    for case, d in errors[:15]:
        print(f"  [{case['intent']} -> {d.action.value} {d.confidence:.2f}"
              f"{' fb' if d.is_fallback else ''}] {case['text']}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int)
    p.add_argument("--concurrency", type=int, default=10)
    a = p.parse_args()
    asyncio.run(run(a.limit, a.concurrency))

