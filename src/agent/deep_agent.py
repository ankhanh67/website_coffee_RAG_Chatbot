"""Orchestrator (DeepAgent): routes incoming chat messages and dispatches to subagents."""

import logging

from src.agent.router import Router
from src.agent.subagent_registry import SubAgentRegistry
from src.observability.logging import dump_json
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

    async def handle(self, request: ChatRequest) -> ChatResponse:
        logger.info("STAGE DeepAgent.handle INPUT: %s", dump_json(request.model_dump(mode="json")))
        decision = await self._router.route(request.message)
        if decision.action is RouterAction.IGNORE:
            response = ChatResponse(
                session_id=request.session_id,
                action=RouterAction.IGNORE,
                reply=self._ignore_reply,
            )
            logger.info("STAGE DeepAgent.handle OUTPUT (ignore): %s", dump_json(response.model_dump(mode="json")))
            return response

        subagent = self._registry.get(decision.action)
        logger.info(
            "STAGE DeepAgent.handle DISPATCH: %s",
            dump_json({"action": decision.action, "subagent": type(subagent).__name__}),
        )
        reply = await subagent.handle(message=request.message, session_id=request.session_id)
        response = ChatResponse(
            session_id=request.session_id,
            action=decision.action,
            reply=reply,
        )
        logger.info("STAGE DeepAgent.handle OUTPUT: %s", dump_json(response.model_dump(mode="json")))
        return response

