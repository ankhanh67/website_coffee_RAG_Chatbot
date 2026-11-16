"""Observability metrics endpoint."""

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter

from src.observability.metrics import metrics_collector

router = APIRouter(tags=["observability"])


@router.get("/metrics")
async def get_metrics() -> dict[str, Any]:
    """Return JSON metrics including latency percentiles, request volume, and cache hit rate."""
    snapshot = metrics_collector.get_snapshot()
    return asdict(snapshot)
