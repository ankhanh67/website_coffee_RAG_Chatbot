"""Orchestrator (DeepAgent): routes incoming chat messages and dispatches to subagents."""

import logging

from src.agent.router import Router
from src.agent.subagent_registry import SubAgentRegistry
from src.exceptions import AgentExecutionError
from src.observability.logging import dump_json
from src.prompt.order_agent import is_short_order_followup
from src.schema.chat import ChatRequest, ChatResponse
from src.schema.router import RouterAction

logger = logging.getLogger(__name__)

IGNORE_REPLY = (
    "Xin chào! Mình có thể hỗ trợ bạn đặt món, tư vấn đồ uống hoặc giải đáp thông tin về quán ạ."
)


class DeepAgent:
    def __init__(
        self,
        router: Router,
        registry: SubAgentRegistry,
        ignore_reply: str = IGNORE_REPLY,
    ) -> None:
        self._router = router
        self._registry = registry
        self._ignore_reply = ignore_reply

    def _should_override_ignore_to_order(self, session_id: str, message: str) -> bool:
        if not is_short_order_followup(message):
            return False
        try:
            order_agent = self._registry.get(RouterAction.ORDER)
        except AgentExecutionError:
            return False
        has_pending = getattr(order_agent, "has_pending_order", None)
        return bool(callable(has_pending) and has_pending(session_id))

    async def handle(self, request: ChatRequest) -> ChatResponse:
        logger.info("STAGE DeepAgent.handle INPUT: %s", dump_json(request.model_dump(mode="json")))
        decision = await self._router.route(request.message)
        action = decision.action

        if action is RouterAction.IGNORE and self._should_override_ignore_to_order(
            request.session_id, request.message
        ):
            logger.info(
                "STAGE DeepAgent.handle OVERRIDE: ignore -> order (pending order confirmation for session_id=%s)",
                request.session_id,
            )
            action = RouterAction.ORDER

        if action is RouterAction.IGNORE:
            response = ChatResponse(
                session_id=request.session_id,
                action=RouterAction.IGNORE,
                reply=self._ignore_reply,
            )
            logger.info("STAGE DeepAgent.handle OUTPUT (ignore): %s", dump_json(response.model_dump(mode="json")))
            return response

        subagent = self._registry.get(action)
        logger.info(
            "STAGE DeepAgent.handle DISPATCH: %s",
            dump_json({"action": action, "subagent": type(subagent).__name__}),
        )
        reply = await subagent.handle(message=request.message, session_id=request.session_id)
        response = ChatResponse(
            session_id=request.session_id,
            action=action,
            reply=reply,
        )
        logger.info("STAGE DeepAgent.handle OUTPUT: %s", dump_json(response.model_dump(mode="json")))
        return response
