"""Supervisor Agent (DeepAgent) built with `langchain.agents.create_agent` and `@tool` subagents."""

import logging
from typing import Any, Protocol

from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.checkpoint.memory import InMemorySaver

from src.agent.router import Router
from src.agent.subagent_registry import SubAgentRegistry
from src.exceptions import AgentExecutionError
from src.observability.logging import dump_json
from src.prompt.deep_agent import DEEP_AGENT_SYSTEM_PROMPT
from src.rag.cache.semantic_cache import SemanticCache
from src.schema.chat import ChatRequest, ChatResponse
from src.schema.router import RouterAction

logger = logging.getLogger(__name__)

IGNORE_REPLY = (
    "Xin chào! Mình có thể hỗ trợ bạn đặt món, tư vấn đồ uống hoặc giải đáp thông tin về quán ạ."
)

_ACTION_TO_TOOL_NAME: dict[RouterAction, str] = {
    RouterAction.ORDER: "call_order_agent",
    RouterAction.CONSULTANT: "call_consultant_agent",
    RouterAction.FAQ: "call_faq_agent",
}


class ChatModelProvider(Protocol):
    def get_chat_model(
        self,
        model: str,
        temperature: float = 0.0,
        model_kwargs: dict[str, Any] | None = None,
    ) -> BaseChatModel: ...


class _RouterGuidedChatModel(BaseChatModel):
    """Lightweight BaseChatModel adapter that dispatches the Jev Router decision as a tool call when no external LLM is injected."""

    target_tool: str
    query: str

    @property
    def _llm_type(self) -> str:
        return "router-guided-chat-model"

    def bind_tools(self, tools: Any, **kwargs: Any) -> BaseChatModel:
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        # Look only at messages since the latest HumanMessage in this turn
        last_human_idx = -1
        for i, m in enumerate(messages):
            if isinstance(m, HumanMessage):
                last_human_idx = i
        current_turn_msgs = messages[last_human_idx + 1 :] if last_human_idx >= 0 else messages
        tool_msgs = [m for m in current_turn_msgs if isinstance(m, ToolMessage)]
        if not tool_msgs:
            ai_msg = AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": self.target_tool,
                        "args": {"query": self.query},
                        "id": "call_subagent_1",
                    }
                ],
            )
        else:
            combined = "\n".join(str(m.content) for m in tool_msgs)
            ai_msg = AIMessage(content=combined)
        return ChatResult(generations=[ChatGeneration(message=ai_msg)])


def build_subagent_tools(
    registry: SubAgentRegistry,
    session_id: str,
    called_actions: list[RouterAction],
) -> list[Any]:
    """Wrap registered SubAgents as LangChain `@tool` functions for the DeepAgent supervisor."""

    @tool
    async def call_order_agent(query: str) -> str:
        """Gọi OrderAgent xử lý đặt món, sửa món, đổi size, xem giỏ hàng, xác nhận hoặc hủy đơn."""
        subagent = registry.get(RouterAction.ORDER)
        logger.info(
            "STAGE DeepAgent.handle DISPATCH: %s",
            dump_json({"action": RouterAction.ORDER, "subagent": type(subagent).__name__}),
        )
        called_actions.append(RouterAction.ORDER)
        return await subagent.handle(message=query, session_id=session_id)

    @tool
    async def call_consultant_agent(query: str) -> str:
        """Gọi ConsultantAgent tư vấn chọn đồ uống, bánh ngọt theo khẩu vị, ngân sách, dị ứng."""
        subagent = registry.get(RouterAction.CONSULTANT)
        logger.info(
            "STAGE DeepAgent.handle DISPATCH: %s",
            dump_json({"action": RouterAction.CONSULTANT, "subagent": type(subagent).__name__}),
        )
        called_actions.append(RouterAction.CONSULTANT)
        return await subagent.handle(message=query, session_id=session_id)

    @tool
    async def call_faq_agent(query: str) -> str:
        """Gọi FAQAgent giải đáp thông tin về quán: giờ mở cửa, chi nhánh, wifi, đỗ xe, khuyến mãi."""
        subagent = registry.get(RouterAction.FAQ)
        logger.info(
            "STAGE DeepAgent.handle DISPATCH: %s",
            dump_json({"action": RouterAction.FAQ, "subagent": type(subagent).__name__}),
        )
        called_actions.append(RouterAction.FAQ)
        return await subagent.handle(message=query, session_id=session_id)

    return [call_order_agent, call_consultant_agent, call_faq_agent]


class DeepAgent:
    def __init__(
        self,
        router: Router,
        registry: SubAgentRegistry,
        model_client: ChatModelProvider | BaseChatModel | None = None,
        model: str = "google/gemini-2.5-flash",
        ignore_reply: str = IGNORE_REPLY,
        semantic_cache: SemanticCache | None = None,
        checkpointer: InMemorySaver | None = None,
    ) -> None:
        self._router = router
        self._registry = registry
        self._model_client = model_client
        self._model = model
        self._ignore_reply = ignore_reply
        self._semantic_cache = semantic_cache
        self._checkpointer = checkpointer or InMemorySaver()
        self._seen_sessions: set[str] = set()

    def _resolve_chat_model(self, routed_action: RouterAction, message: str) -> BaseChatModel:
        if isinstance(self._model_client, BaseChatModel):
            return self._model_client
        if self._model_client is not None:
            return self._model_client.get_chat_model(model=self._model, temperature=0.0)
        target_tool = _ACTION_TO_TOOL_NAME.get(routed_action, "call_faq_agent")
        return _RouterGuidedChatModel(target_tool=target_tool, query=message)

    def _should_override_ignore_to_order(self, session_id: str, message: str) -> bool:
        text = message.strip()
        if not text or len(text) > 100:
            return False
        try:
            order_agent = self._registry.get(RouterAction.ORDER)
        except AgentExecutionError:
            return False
        has_pending = getattr(order_agent, "has_pending_order", None)
        return bool(callable(has_pending) and has_pending(session_id))

    async def handle(self, request: ChatRequest) -> ChatResponse:
        logger.info(
            "STAGE DeepAgent.handle INPUT: %s", dump_json(request.model_dump(mode="json"))
        )
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
        elif (
            action is RouterAction.IGNORE
            and request.session_id in self._seen_sessions
            and self._model_client is not None
        ):
            logger.info(
                "STAGE DeepAgent.handle OVERRIDE: ignore -> consultant (active multi-turn session_id=%s)",
                request.session_id,
            )
            action = RouterAction.CONSULTANT

        if action is RouterAction.IGNORE:
            response = ChatResponse(
                session_id=request.session_id,
                action=RouterAction.IGNORE,
                reply=self._ignore_reply,
            )
            logger.info(
                "STAGE DeepAgent.handle OUTPUT (ignore): %s",
                dump_json(response.model_dump(mode="json")),
            )
            return response

        # Check SemanticCache only for non-stateful routes (CONSULTANT / FAQ)
        if self._semantic_cache is not None and self._semantic_cache.is_cacheable(action):
            cached = await self._semantic_cache.lookup(request.message)
            if cached is not None:
                entry, _ = cached
                response = ChatResponse(
                    session_id=request.session_id,
                    action=entry.action,
                    reply=entry.reply,
                )
                logger.info(
                    "STAGE DeepAgent.handle OUTPUT (cache_hit): %s",
                    dump_json(response.model_dump(mode="json")),
                )
                return response

        called_actions: list[RouterAction] = []
        tools = build_subagent_tools(self._registry, request.session_id, called_actions)
        chat_model = self._resolve_chat_model(action, request.message)

        supervisor_agent = create_agent(
            model=chat_model,
            tools=tools,
            system_prompt=f"{DEEP_AGENT_SYSTEM_PROMPT}\nGợi ý phân luồng từ Router: {action.value}",
            checkpointer=self._checkpointer,
        )

        result = await supervisor_agent.ainvoke(
            {"messages": [{"role": "user", "content": request.message}]},
            config={"configurable": {"thread_id": f"supervisor:{request.session_id}"}},
        )
        self._seen_sessions.add(request.session_id)
        messages = result.get("messages", [])
        reply = str(messages[-1].content).strip() if messages else ""
        final_action = called_actions[-1] if called_actions else action

        # Store in SemanticCache only when a single cacheable intent was executed (never ORDER)
        if (
            self._semantic_cache is not None
            and RouterAction.ORDER not in called_actions
            and self._semantic_cache.is_cacheable(final_action)
        ):
            await self._semantic_cache.store(request.message, final_action, reply)

        response = ChatResponse(
            session_id=request.session_id,
            action=final_action,
            reply=reply,
        )
        logger.info("STAGE DeepAgent.handle OUTPUT: %s", dump_json(response.model_dump(mode="json")))
        return response
