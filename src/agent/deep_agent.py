"""Orchestrator (DeepAgent): LangGraph StateGraph routing chat messages to specialized subagent nodes."""

import logging
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

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


class AgentGraphState(TypedDict):
    """State dictionary passed across nodes in the DeepAgent LangGraph workflow."""

    session_id: str
    message: str
    action: RouterAction
    reply: str


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
        self._graph: CompiledStateGraph = self._build_graph()

    @property
    def graph(self) -> CompiledStateGraph:
        """Expose the compiled LangGraph state machine."""
        return self._graph

    def _build_graph(self) -> CompiledStateGraph:
        workflow = StateGraph(AgentGraphState)

        workflow.add_node("router", self._router_node)
        workflow.add_node("order", self._order_node)
        workflow.add_node("consultant", self._consultant_node)
        workflow.add_node("faq", self._faq_node)
        workflow.add_node("ignore", self._ignore_node)

        workflow.add_edge(START, "router")
        workflow.add_conditional_edges(
            "router",
            self._route_by_action,
            {
                RouterAction.ORDER.value: "order",
                RouterAction.CONSULTANT.value: "consultant",
                RouterAction.FAQ.value: "faq",
                RouterAction.IGNORE.value: "ignore",
            },
        )
        workflow.add_edge("order", END)
        workflow.add_edge("consultant", END)
        workflow.add_edge("faq", END)
        workflow.add_edge("ignore", END)

        return workflow.compile()

    def _should_override_ignore_to_order(self, session_id: str, message: str) -> bool:
        if not is_short_order_followup(message):
            return False
        try:
            order_agent = self._registry.get(RouterAction.ORDER)
        except AgentExecutionError:
            return False
        has_pending = getattr(order_agent, "has_pending_order", None)
        return bool(callable(has_pending) and has_pending(session_id))

    async def _router_node(self, state: AgentGraphState) -> dict[str, Any]:
        decision = await self._router.route(state["message"])
        action = decision.action

        if action is RouterAction.IGNORE and self._should_override_ignore_to_order(
            state["session_id"], state["message"]
        ):
            logger.info(
                "STAGE DeepAgent.handle OVERRIDE: ignore -> order (pending order confirmation for session_id=%s)",
                state["session_id"],
            )
            action = RouterAction.ORDER

        return {"action": action}

    @staticmethod
    def _route_by_action(state: AgentGraphState) -> str:
        return state["action"].value

    async def _dispatch_subagent(
        self, action: RouterAction, state: AgentGraphState
    ) -> dict[str, Any]:
        subagent = self._registry.get(action)
        logger.info(
            "STAGE DeepAgent.handle DISPATCH: %s",
            dump_json({"action": action, "subagent": type(subagent).__name__}),
        )
        reply = await subagent.handle(message=state["message"], session_id=state["session_id"])
        return {"reply": reply}

    async def _order_node(self, state: AgentGraphState) -> dict[str, Any]:
        return await self._dispatch_subagent(RouterAction.ORDER, state)

    async def _consultant_node(self, state: AgentGraphState) -> dict[str, Any]:
        return await self._dispatch_subagent(RouterAction.CONSULTANT, state)

    async def _faq_node(self, state: AgentGraphState) -> dict[str, Any]:
        return await self._dispatch_subagent(RouterAction.FAQ, state)

    async def _ignore_node(self, state: AgentGraphState) -> dict[str, Any]:
        return {"reply": self._ignore_reply}

    async def handle(self, request: ChatRequest) -> ChatResponse:
        logger.info(
            "STAGE DeepAgent.handle INPUT: %s", dump_json(request.model_dump(mode="json"))
        )
        initial_state: AgentGraphState = {
            "session_id": request.session_id,
            "message": request.message,
            "action": RouterAction.IGNORE,
            "reply": "",
        }
        final_state = await self._graph.ainvoke(initial_state)
        action = final_state["action"]
        response = ChatResponse(
            session_id=request.session_id,
            action=action,
            reply=final_state["reply"],
        )
        if action is RouterAction.IGNORE:
            logger.info(
                "STAGE DeepAgent.handle OUTPUT (ignore): %s",
                dump_json(response.model_dump(mode="json")),
            )
        else:
            logger.info(
                "STAGE DeepAgent.handle OUTPUT: %s",
                dump_json(response.model_dump(mode="json")),
            )
        return response
