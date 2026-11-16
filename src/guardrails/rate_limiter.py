"""In-memory rate limiter guardrail for API endpoints."""

import time
from collections import defaultdict
from threading import Lock


class RateLimiter:
    """Sliding-window in-memory rate limiter per client identifier."""

    def __init__(self, max_requests: int = 60, window_seconds: float = 60.0) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._lock = Lock()
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, client_id: str) -> tuple[bool, int]:
        """Check if client is permitted to make a request.

        Returns (allowed, retry_after_seconds).
        """
        now = time.time()
        cutoff = now - self._window_seconds

        with self._lock:
            timestamps = self._requests[client_id]
            # Discard timestamps outside the current window
            while timestamps and timestamps[0] <= cutoff:
                timestamps.pop(0)

            if len(timestamps) >= self._max_requests:
                oldest = timestamps[0]
                retry_after = max(1, int(oldest + self._window_seconds - now))
                return False, retry_after

            timestamps.append(now)
            return True, 0

    def reset(self) -> None:
        with self._lock:
            self._requests.clear()


# Default singleton instance: 60 requests per 60s per client
api_rate_limiter = RateLimiter(max_requests=60, window_seconds=60.0)
