"""Application service for handling customer chat messages."""

import logging
import time
from contextlib import nullcontext

from src.agent.deep_agent import DeepAgent
from src.observability.logging import dump_json, get_job_id, job_context
from src.schema.chat import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, deep_agent: DeepAgent) -> None:
        self._deep_agent = deep_agent

    async def chat(self, request: ChatRequest) -> ChatResponse:
        ctx = nullcontext(get_job_id()) if get_job_id() else job_context()
        with ctx:
            t0 = time.perf_counter()
            logger.info(
                "STAGE ChatService.chat INPUT: %s",
                dump_json(request.model_dump(mode="json")),
            )
            response = await self._deep_agent.handle(request)
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
            logger.info(
                "STAGE ChatService.chat OUTPUT: %s",
                dump_json({"elapsed_ms": elapsed_ms, "response": response.model_dump(mode="json")}),
            )
            return response
