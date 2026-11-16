"""Unit tests for sliding-window rate limiter."""

from src.guardrails.rate_limiter import RateLimiter


def test_rate_limiter_allows_under_limit():
    limiter = RateLimiter(max_requests=5, window_seconds=10.0)
    for _ in range(5):
        allowed, retry_after = limiter.is_allowed("client-1")
        assert allowed is True
        assert retry_after == 0


def test_rate_limiter_blocks_when_exceeded():
    limiter = RateLimiter(max_requests=3, window_seconds=5.0)
    for _ in range(3):
        allowed, _ = limiter.is_allowed("client-2")
        assert allowed is True

    # 4th request must be blocked
    allowed, retry_after = limiter.is_allowed("client-2")
    assert allowed is False
    assert retry_after > 0


def test_rate_limiter_differentiates_clients():
    limiter = RateLimiter(max_requests=2, window_seconds=5.0)
    limiter.is_allowed("user-a")
    limiter.is_allowed("user-a")
    allowed_a, _ = limiter.is_allowed("user-a")
    assert allowed_a is False

    # user-b has separate quota
    allowed_b, _ = limiter.is_allowed("user-b")
    assert allowed_b is True
