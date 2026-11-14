"""OrderAgent: extracts customer order intent via LLM, calculates deterministically via OrderService, and asks for confirmation."""

import logging
from typing import Protocol, TypeVar

from pydantic import BaseModel

from src.observability.logging import dump_json
from src.prompt.order_agent import (
    build_order_extraction_system_prompt,
    format_order_response,
)
from src.schema.order import OrderExtraction
from src.schema.router import RouterAction
from src.services.order_service import OrderService
from src.subagents.base import BaseSubAgent

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class StructuredLLMClient(Protocol):
    async def generate_structured(
        self,
        model: str,
        system_prompt: str,
        user_message: str,
        response_model: type[T],
        temperature: float = 0.0,
    ) -> T: ...


class OrderAgent(BaseSubAgent):
    action = RouterAction.ORDER

    def __init__(
        self,
        model_client: StructuredLLMClient,
        order_service: OrderService,
        model: str = "google/gemini-2.5-flash",
    ) -> None:
        self._model_client = model_client
        self._order_service = order_service
        self._model = model

    def has_pending_order(self, session_id: str) -> bool:
        return self._order_service.has_pending_order(session_id)

    async def handle(self, message: str, session_id: str) -> str:
        logger.info(
            "STAGE OrderAgent.handle INPUT: %s",
            dump_json({"session_id": session_id, "message": message, "model": self._model}),
        )
        extraction = await self._model_client.generate_structured(
            model=self._model,
            system_prompt=build_order_extraction_system_prompt(),
            user_message=message,
            response_model=OrderExtraction,
        )
        calculation = await self._order_service.process_extraction(
            session_id=session_id,
            extraction=extraction,
        )
        reply = format_order_response(calculation)
        logger.info(
            "STAGE OrderAgent.handle OUTPUT: %s",
            dump_json(
                {
                    "session_id": session_id,
                    "status": calculation.status,
                    "total_vnd": calculation.total_vnd,
                    "reply": reply,
                }
            ),
        )
        return reply

