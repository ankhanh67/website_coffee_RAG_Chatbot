"""Application service for handling customer chat messages."""

import logging
import time
from contextlib import nullcontext

from src.agent.deep_agent import DeepAgent
from src.observability.logging import dump_json, get_job_id, job_context
from src.observability.tracing import trace_chat_request
from src.schema.chat import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, deep_agent: DeepAgent) -> None:
        self._deep_agent = deep_agent

    async def chat(self, request: ChatRequest) -> ChatResponse:
        ctx = nullcontext(get_job_id()) if get_job_id() else job_context()
        with (
            ctx as active_job_id,
            trace_chat_request(
                session_id=request.session_id,
                message=request.message,
                job_id=active_job_id,
            ) as root_span,
        ):
            t0 = time.perf_counter()
            logger.info(
                "STAGE ChatService.chat INPUT: %s",
                dump_json(request.model_dump(mode="json")),
            )
            response = await self._deep_agent.handle(request)
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
            root_span.update(
                output=response.model_dump(mode="json"),
                metadata={"elapsed_ms": elapsed_ms, "action": response.action.value},
            )
            logger.info(
                "STAGE ChatService.chat OUTPUT: %s",
                dump_json(
                    {"elapsed_ms": elapsed_ms, "response": response.model_dump(mode="json")}
                ),
            )
            return response
