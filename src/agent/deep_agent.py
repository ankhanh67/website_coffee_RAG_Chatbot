"""Orchestrator (DeepAgent): routes incoming chat messages and dispatches to subagents."""

from src.agent.router import Router
from src.agent.subagent_registry import SubAgentRegistry
from src.schema.chat import ChatRequest, ChatResponse
from src.schema.router import RouterAction

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
        decision = await self._router.route(request.message)
        if decision.action is RouterAction.IGNORE:
            return ChatResponse(
                session_id=request.session_id,
                action=RouterAction.IGNORE,
                reply=self._ignore_reply,
            )

        subagent = self._registry.get(decision.action)
        reply = await subagent.handle(message=request.message, session_id=request.session_id)
        return ChatResponse(
            session_id=request.session_id,
            action=decision.action,
            reply=reply,
        )
