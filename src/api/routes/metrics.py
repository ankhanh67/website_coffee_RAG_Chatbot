"""Observability metrics endpoint."""

from fastapi import APIRouter

from src.observability.metrics import MetricsSnapshot, metrics_collector

router = APIRouter(tags=["observability"])


@router.get("/metrics", response_model=MetricsSnapshot)
async def get_metrics() -> MetricsSnapshot:
    """Return JSON metrics including latency percentiles, request volume, and cache hit rate."""
    return metrics_collector.get_snapshot()
