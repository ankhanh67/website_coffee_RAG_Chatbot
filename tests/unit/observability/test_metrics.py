"""Unit tests for MetricsCollector and metrics calculations."""

from src.observability.metrics import MetricsCollector


def test_metrics_collector_records_requests_and_latency():
    collector = MetricsCollector()

    collector.record_request_start()
    assert collector.get_snapshot().active_connections == 1
    assert collector.get_snapshot().total_requests == 1

    collector.record_request_end(elapsed_ms=100.0, is_success=True)
    assert collector.get_snapshot().active_connections == 0
    assert collector.get_snapshot().successful_requests == 1
    assert collector.get_snapshot().avg_latency_ms == 100.0


def test_metrics_collector_cache_hit_rate():
    collector = MetricsCollector()
    collector.record_cache_hit()
    collector.record_cache_miss()
    collector.record_cache_hit()

    snapshot = collector.get_snapshot()
    assert snapshot.cache_hits == 2
    assert snapshot.cache_misses == 1
    # 2 / 3 = 66.7%
    assert snapshot.cache_hit_rate_pct == 66.7


def test_metrics_collector_p95_latency():
    collector = MetricsCollector()
    # Add 100 latencies from 1ms to 100ms
    for i in range(1, 101):
        collector.record_request_start()
        collector.record_request_end(float(i), is_success=True)

    snapshot = collector.get_snapshot()
    assert snapshot.total_requests == 100
    assert snapshot.p95_latency_ms == 96.0 or snapshot.p95_latency_ms == 95.0
