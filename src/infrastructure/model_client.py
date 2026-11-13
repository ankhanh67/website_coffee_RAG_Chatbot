"""HTTP client for OpenRouter: Jev Decisions API + Chat Completions (text & structured JSON)."""

import asyncio
import logging
import re
import time
from typing import TypeVar

import httpx2 as httpx
from pydantic import BaseModel, ValidationError

from src.exceptions import ModelServiceUnavailableError
from src.observability.logging import dump_json

logger = logging.getLogger(__name__)
RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}
T = TypeVar("T", bound=BaseModel)

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def _strip_json_fences(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = _CODE_FENCE_RE.sub("", text).strip()
    return text


class ModelClient:
    def __init__(
        self,
        api_key: str,
        decisions_url: str,
        timeout_seconds: float,
        max_retries: int,
        base_url: str = "https://openrouter.ai/api/v1",
        transport: httpx.AsyncBaseTransport | None = None,
        retry_backoff_seconds: float = 0.5,
    ):
        self._decisions_url = decisions_url
        self._chat_url = f"{base_url.rstrip('/')}/chat/completions"
        self._max_retries = max_retries
        self._backoff = retry_backoff_seconds
        self._http = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout_seconds,
            transport=transport,
        )

    async def _post_with_retry(self, url: str, payload: dict, stage_name: str) -> dict:
        logger.info("STAGE %s INPUT: %s", stage_name, dump_json({"url": url, "payload": payload}))
        last_error = ""
        for attempt in range(self._max_retries + 1):
            if attempt:
                logger.warning("Retrying %s (attempt %d/%d) after: %s", stage_name, attempt, self._max_retries, last_error)
                await asyncio.sleep(self._backoff * 2 ** (attempt - 1))
            t0 = time.perf_counter()
            try:
                resp = await self._http.post(url, json=payload)
            except httpx.TransportError as e:
                last_error = f"{type(e).__name__}: {e}"
                continue
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
            if resp.status_code in RETRYABLE_STATUS:
                last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                continue
            if resp.is_error:
                logger.error("STAGE %s ERROR: status=%d body=%s", stage_name, resp.status_code, resp.text[:300])
                raise ModelServiceUnavailableError(f"HTTP {resp.status_code}: {resp.text[:200]}")
            data = resp.json()
            logger.info(
                "STAGE %s OUTPUT: %s",
                stage_name,
                dump_json({"status": resp.status_code, "elapsed_ms": elapsed_ms, "response": data}),
            )
            return data
        raise ModelServiceUnavailableError(
            f"{stage_name} failed after {self._max_retries + 1} attempts: {last_error}"
        )

    async def decide(self, model: str, state: dict, questions: dict) -> dict:
        """Call a System One model (Jev). Returns the raw JSON response (answers, usage, ...)."""
        payload = {"model": model, "state": state, "questions": questions}
        return await self._post_with_retry(self._decisions_url, payload, "ModelClient.decide")

    async def generate_text(
        self,
        model: str,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.2,
    ) -> str:
        """Call OpenRouter Chat Completions and return the assistant reply string."""
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": temperature,
        }
        data = await self._post_with_retry(self._chat_url, payload, "ModelClient.generate_text")
        try:
            content = data["choices"][0]["message"]["content"]
            return str(content).strip()
        except (KeyError, IndexError, TypeError) as e:
            raise ModelServiceUnavailableError(f"Malformed chat completion response: {e}") from e

    async def generate_structured(
        self,
        model: str,
        system_prompt: str,
        user_message: str,
        response_model: type[T],
        temperature: float = 0.0,
    ) -> T:
        """Call OpenRouter Chat Completions in JSON mode and validate into `response_model`."""
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        data = await self._post_with_retry(self._chat_url, payload, "ModelClient.generate_structured")
        try:
            raw_content = str(data["choices"][0]["message"]["content"])
            cleaned = _strip_json_fences(raw_content)
            return response_model.model_validate_json(cleaned)
        except (KeyError, IndexError, TypeError, ValidationError) as e:
            logger.error("Failed to parse structured output for %s: %s", response_model.__name__, e)
            raise ModelServiceUnavailableError(
                f"Structured output validation failed for {response_model.__name__}: {e}"
            ) from e

    async def aclose(self) -> None:
        await self._http.aclose()
