"""Client for OpenRouter: Jev Decisions API + LangChain ChatOpenAI (LCEL text & structured chains)."""

import asyncio
import logging
import time
from typing import Any, TypeVar

import httpx2 as httpx
from langchain_openai import ChatOpenAI
from openai import OpenAIError
from pydantic import BaseModel, ValidationError

from src.agent.llm import (
    build_chat_model,
    build_structured_chain,
    build_text_chain,
    strip_json_fences,
)
from src.exceptions import ModelServiceUnavailableError
from src.observability.logging import dump_json

logger = logging.getLogger(__name__)
RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}
T = TypeVar("T", bound=BaseModel)

# Keep backward-compatible helper alias
_strip_json_fences = strip_json_fences


class ModelClient:
    def __init__(
        self,
        api_key: str,
        decisions_url: str = "https://openrouter.ai/api/alpha/decisions",
        timeout_seconds: float = 30.0,
        max_retries: int = 2,
        base_url: str = "https://openrouter.ai/api/v1",
        transport: httpx.AsyncBaseTransport | None = None,
        retry_backoff_seconds: float = 0.5,
    ):
        self._api_key = api_key
        self._decisions_url = decisions_url
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._backoff = retry_backoff_seconds
        self._http = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout_seconds,
            transport=transport,
        )

    def get_chat_model(
        self,
        model: str,
        temperature: float = 0.0,
        model_kwargs: dict[str, Any] | None = None,
    ) -> ChatOpenAI:
        """Create a LangChain ChatOpenAI instance sharing this client's async HTTP transport."""
        return build_chat_model(
            model=model,
            api_key=self._api_key,
            base_url=self._base_url,
            temperature=temperature,
            timeout_seconds=self._timeout_seconds,
            max_retries=self._max_retries,
            http_async_client=self._http,
            model_kwargs=model_kwargs,
        )

    async def _post_with_retry(self, url: str, payload: dict, stage_name: str) -> dict:
        logger.info("STAGE %s INPUT: %s", stage_name, dump_json({"url": url, "payload": payload}))
        last_error = ""
        for attempt in range(self._max_retries + 1):
            if attempt:
                logger.warning(
                    "Retrying %s (attempt %d/%d) after: %s",
                    stage_name,
                    attempt,
                    self._max_retries,
                    last_error,
                )
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
                logger.error(
                    "STAGE %s ERROR: status=%d body=%s",
                    stage_name,
                    resp.status_code,
                    resp.text[:300],
                )
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
        """Execute a LangChain LCEL text generation chain (ChatPromptTemplate | ChatOpenAI | StrOutputParser)."""
        logger.info(
            "STAGE ModelClient.generate_text INPUT: %s",
            dump_json({"model": model, "temperature": temperature, "user_message": user_message}),
        )
        t0 = time.perf_counter()
        try:
            chat_model = self.get_chat_model(model=model, temperature=temperature)
            chain = build_text_chain(chat_model)
            reply = await chain.ainvoke(
                {"system_prompt": system_prompt, "user_message": user_message}
            )
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
            logger.info(
                "STAGE ModelClient.generate_text OUTPUT: %s",
                dump_json({"elapsed_ms": elapsed_ms, "reply": reply}),
            )
            return reply
        except (OpenAIError, httpx.HTTPError, ValidationError, KeyError, IndexError, TypeError) as e:
            logger.error("STAGE ModelClient.generate_text ERROR: %s", e)
            raise ModelServiceUnavailableError(f"Chat completion failed: {e}") from e

    async def generate_structured(
        self,
        model: str,
        system_prompt: str,
        user_message: str,
        response_model: type[T],
        temperature: float = 0.0,
    ) -> T:
        """Execute a LangChain LCEL structured output chain into `response_model`."""
        logger.info(
            "STAGE ModelClient.generate_structured INPUT: %s",
            dump_json(
                {
                    "model": model,
                    "response_model": response_model.__name__,
                    "user_message": user_message,
                }
            ),
        )
        t0 = time.perf_counter()
        try:
            chat_model = self.get_chat_model(
                model=model,
                temperature=temperature,
                model_kwargs={"response_format": {"type": "json_object"}},
            )
            chain = build_structured_chain(chat_model, response_model)
            result = await chain.ainvoke(
                {"system_prompt": system_prompt, "user_message": user_message}
            )
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
            logger.info(
                "STAGE ModelClient.generate_structured OUTPUT: %s",
                dump_json(
                    {
                        "elapsed_ms": elapsed_ms,
                        "response_model": response_model.__name__,
                        "result": result.model_dump(mode="json"),
                    }
                ),
            )
            return result
        except (OpenAIError, httpx.HTTPError, ValidationError, KeyError, IndexError, TypeError) as e:
            logger.error("Failed to parse structured output for %s: %s", response_model.__name__, e)
            raise ModelServiceUnavailableError(
                f"Structured output validation failed for {response_model.__name__}: {e}"
            ) from e

    async def aclose(self) -> None:
        await self._http.aclose()
