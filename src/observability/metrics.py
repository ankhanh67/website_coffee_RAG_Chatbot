"""In-memory metrics tracker for application latency, throughput, and cache efficiency."""

import time
from dataclasses import dataclass
from threading import Lock


@dataclass
class MetricsSnapshot:
    uptime_seconds: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    cache_hits: int
    cache_misses: int
    cache_hit_rate_pct: float
    avg_latency_ms: float
    p95_latency_ms: float
    active_connections: int


class MetricsCollector:
    """Thread-safe in-memory performance and usage metrics collector."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._start_time = time.time()
        self._total_requests: int = 0
        self._successful_requests: int = 0
        self._failed_requests: int = 0
        self._cache_hits: int = 0
        self._cache_misses: int = 0
        self._latencies_ms: list[float] = []
        self._active_connections: int = 0

    def record_request_start(self) -> None:
        with self._lock:
            self._total_requests += 1
            self._active_connections += 1

    def record_request_end(self, elapsed_ms: float, is_success: bool = True) -> None:
        with self._lock:
            self._active_connections = max(0, self._active_connections - 1)
            if is_success:
                self._successful_requests += 1
            else:
                self._failed_requests += 1

            self._latencies_ms.append(elapsed_ms)
            # Retain sliding window of last 1000 latencies
            if len(self._latencies_ms) > 1000:
                self._latencies_ms = self._latencies_ms[-1000:]

    def record_cache_hit(self) -> None:
        with self._lock:
            self._cache_hits += 1

    def record_cache_miss(self) -> None:
        with self._lock:
            self._cache_misses += 1

    def get_snapshot(self) -> MetricsSnapshot:
        with self._lock:
            now = time.time()
            uptime = round(now - self._start_time, 1)
            total_cache = self._cache_hits + self._cache_misses
            hit_rate = round((self._cache_hits / total_cache * 100), 1) if total_cache > 0 else 0.0

            if self._latencies_ms:
                sorted_lat = sorted(self._latencies_ms)
                avg_lat = round(sum(sorted_lat) / len(sorted_lat), 1)
                p95_idx = int(len(sorted_lat) * 0.95)
                p95_lat = round(sorted_lat[min(p95_idx, len(sorted_lat) - 1)], 1)
            else:
                avg_lat = 0.0
                p95_lat = 0.0

            return MetricsSnapshot(
                uptime_seconds=uptime,
                total_requests=self._total_requests,
                successful_requests=self._successful_requests,
                failed_requests=self._failed_requests,
                cache_hits=self._cache_hits,
                cache_misses=self._cache_misses,
                cache_hit_rate_pct=hit_rate,
                avg_latency_ms=avg_lat,
                p95_latency_ms=p95_lat,
                active_connections=self._active_connections,
            )

    def reset(self) -> None:
        with self._lock:
            self._start_time = time.time()
            self._total_requests = 0
            self._successful_requests = 0
            self._failed_requests = 0
            self._cache_hits = 0
            self._cache_misses = 0
            self._latencies_ms.clear()
            self._active_connections = 0


metrics_collector = MetricsCollector()
