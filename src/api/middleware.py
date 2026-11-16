"""HTTP middlewares for request context, metrics tracking, and rate limiting."""

import logging
import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from src.guardrails.rate_limiter import api_rate_limiter
from src.observability.logging import dump_json, job_context
from src.observability.metrics import metrics_collector

logger = logging.getLogger(__name__)


async def rate_limit_and_metrics_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Track request latency and enforce sliding-window rate limit on /api/ endpoints."""
    path = request.url.path
    if not path.startswith("/api/"):
        return await call_next(request)

    # Determine client identifier from client IP or header
    client_ip = request.client.host if request.client else "unknown"
    client_id = request.headers.get("X-Forwarded-For", client_ip).split(",")[0].strip()

    # Check Rate Limiter
    allowed, retry_after = api_rate_limiter.is_allowed(client_id)
    if not allowed:
        logger.warning(
            "STAGE RateLimiter BLOCKED: client_id=%s path=%s retry_after=%ds",
            client_id,
            path,
            retry_after,
        )
        return JSONResponse(
            status_code=429,
            content={"detail": "Too Many Requests. Please slow down.", "retry_after": retry_after},
            headers={"Retry-After": str(retry_after)},
        )

    # Bind Job ID Context & Record Metrics
    with job_context(request.headers.get("X-Job-ID")) as job_id:
        t0 = time.perf_counter()
        metrics_collector.record_request_start()
        logger.info(
            "STAGE HTTP INPUT: %s",
            dump_json({"method": request.method, "path": path, "job_id": job_id, "client_id": client_id}),
        )

        is_success = True
        try:
            response = await call_next(request)
            if response.status_code >= 500:
                is_success = False
            response.headers["X-Job-ID"] = job_id
            return response
        except Exception:
            is_success = False
            raise
        finally:
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
            metrics_collector.record_request_end(elapsed_ms, is_success=is_success)
            logger.info(
                "STAGE HTTP OUTPUT: %s",
                dump_json({"path": path, "job_id": job_id, "elapsed_ms": elapsed_ms, "success": is_success}),
            )
