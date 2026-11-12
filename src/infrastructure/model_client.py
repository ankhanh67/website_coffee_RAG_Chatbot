"""HTTP client for OpenRouter. Phase 1 only needs Jev via the Decisions API."""

import asyncio
import logging
import time

import httpx2 as httpx

from src.exceptions import ModelServiceUnavailableError
from src.observability.logging import dump_json

logger = logging.getLogger(__name__)
RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}


class ModelClient:
    def __init__(
        self,
        api_key: str,
        decisions_url: str,
        timeout_seconds: float,
        max_retries: int,
        transport: httpx.AsyncBaseTransport | None = None,
        retry_backoff_seconds: float = 0.5,
    ):
        self._decisions_url = decisions_url
        self._max_retries = max_retries
        self._backoff = retry_backoff_seconds
        self._http = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout_seconds,
            transport=transport,
        )

    async def decide(self, model: str, state: dict, questions: dict) -> dict:
        """Call a System One model (Jev). Returns the raw JSON response (answers, usage, ...)."""
        payload = {"model": model, "state": state, "questions": questions}
        logger.info("STAGE ModelClient.decide INPUT: %s", dump_json({"url": self._decisions_url, "payload": payload}))
        last_error = ""
        for attempt in range(self._max_retries + 1):
            if attempt:
                logger.warning("Retrying Decisions API (attempt %d/%d) after: %s", attempt, self._max_retries, last_error)
                await asyncio.sleep(self._backoff * 2 ** (attempt - 1))
            t0 = time.perf_counter()
            try:
                resp = await self._http.post(self._decisions_url, json=payload)
            except httpx.TransportError as e:  # includes timeouts
                last_error = f"{type(e).__name__}: {e}"
                continue
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
            if resp.status_code in RETRYABLE_STATUS:
                last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                continue
            if resp.is_error:
                logger.error("STAGE ModelClient.decide ERROR: status=%d body=%s", resp.status_code, resp.text[:300])
                raise ModelServiceUnavailableError(f"HTTP {resp.status_code}: {resp.text[:200]}")
            data = resp.json()
            logger.info(
                "STAGE ModelClient.decide OUTPUT: %s",
                dump_json({"status": resp.status_code, "elapsed_ms": elapsed_ms, "response": data}),
            )
            return data
        raise ModelServiceUnavailableError(
            f"Decisions API failed after {self._max_retries + 1} attempts: {last_error}"
        )

    async def aclose(self) -> None:
        await self._http.aclose()

