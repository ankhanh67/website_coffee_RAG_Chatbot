"""OrderAgent built with `langchain.agents.create_agent` and `@tool`."""

import logging
from typing import Any, Protocol

from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.checkpoint.memory import InMemorySaver

from src.observability.logging import dump_json
from src.prompt.order_agent import ORDER_AGENT_SYSTEM_PROMPT
from src.schema.order import OrderExtraction, OrderIntentType, OrderItemInput
from src.schema.router import RouterAction
from src.services.order_service import OrderService
from src.subagents.base import BaseSubAgent

logger = logging.getLogger(__name__)


class ChatModelProvider(Protocol):
    def get_chat_model(
        self,
        model: str,
        temperature: float = 0.0,
        model_kwargs: dict[str, Any] | None = None,
    ) -> BaseChatModel: ...


def build_order_tools(order_service: OrderService, session_id: str) -> list[Any]:
    """Create LangChain `@tool` functions bound to `order_service` and `session_id`."""

    @tool
    async def add_order_items(items: list[OrderItemInput]) -> str:
        """Thêm một hoặc nhiều món mới vào giỏ hàng tạm tính của khách hàng."""
        added = [item.model_copy(update={"action": OrderIntentType.ADD}) for item in items]
        calc = await order_service.process_extraction(
            session_id=session_id,
            extraction=OrderExtraction(intent=OrderIntentType.ADD, items=added),
        )
        return calc.model_dump_json()

    @tool
    async def update_order_items(items: list[OrderItemInput]) -> str:
        """Đổi size (S/M/L) hoặc cập nhật số lượng cho món đã có trong giỏ hàng."""
        updated = [item.model_copy(update={"action": OrderIntentType.UPDATE}) for item in items]
        calc = await order_service.process_extraction(
            session_id=session_id,
            extraction=OrderExtraction(intent=OrderIntentType.UPDATE, items=updated),
        )
        return calc.model_dump_json()

    @tool
    async def remove_order_items(items: list[OrderItemInput]) -> str:
        """Xóa hoặc bỏ một hay nhiều món khỏi giỏ hàng của khách."""
        removed = [item.model_copy(update={"action": OrderIntentType.REMOVE}) for item in items]
        calc = await order_service.process_extraction(
            session_id=session_id,
            extraction=OrderExtraction(intent=OrderIntentType.REMOVE, items=removed),
        )
        return calc.model_dump_json()

    @tool
    async def confirm_order() -> str:
        """Xác nhận chốt đơn hàng hiện tại khi khách đồng ý."""
        calc = await order_service.process_extraction(
            session_id=session_id,
            extraction=OrderExtraction(intent=OrderIntentType.CONFIRM, items=[]),
        )
        return calc.model_dump_json()

    @tool
    async def cancel_order() -> str:
        """Hủy toàn bộ đơn hàng / xóa sạch giỏ hàng khi khách không muốn đặt nữa."""
        calc = await order_service.process_extraction(
            session_id=session_id,
            extraction=OrderExtraction(intent=OrderIntentType.CANCEL, items=[]),
        )
        return calc.model_dump_json()

    @tool
    async def view_order() -> str:
        """Xem lại hoặc kiểm tra các món đang có trong giỏ hàng hiện tại của khách."""
        calc = await order_service.process_extraction(
            session_id=session_id,
            extraction=OrderExtraction(intent=OrderIntentType.VIEW, items=[]),
        )
        return calc.model_dump_json()

    return [
        add_order_items,
        update_order_items,
        remove_order_items,
        confirm_order,
        cancel_order,
        view_order,
    ]


class OrderAgent(BaseSubAgent):
    action = RouterAction.ORDER

    def __init__(
        self,
        model_client: ChatModelProvider | BaseChatModel,
        order_service: OrderService,
        model: str = "google/gemini-2.5-flash",
        checkpointer: InMemorySaver | None = None,
    ) -> None:
        self._model_client = model_client
        self._order_service = order_service
        self._model = model
        self._checkpointer = checkpointer or InMemorySaver()

    def _resolve_chat_model(self) -> BaseChatModel:
        if isinstance(self._model_client, BaseChatModel):
            return self._model_client
        return self._model_client.get_chat_model(model=self._model, temperature=0.2)

    def has_pending_order(self, session_id: str) -> bool:
        return self._order_service.has_pending_order(session_id)

    async def handle(self, message: str, session_id: str) -> str:
        logger.info(
            "STAGE OrderAgent.handle INPUT: %s",
            dump_json({"session_id": session_id, "message": message, "model": self._model}),
        )
        chat_model = self._resolve_chat_model()
        tools = build_order_tools(self._order_service, session_id)
        agent = create_agent(
            model=chat_model,
            tools=tools,
            system_prompt=ORDER_AGENT_SYSTEM_PROMPT,
            checkpointer=self._checkpointer,
        )

        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": message}]},
            config={"configurable": {"thread_id": f"order:{session_id}"}},
        )
        messages = result.get("messages", [])
        reply = str(messages[-1].content).strip() if messages else ""

        logger.info(
            "STAGE OrderAgent.handle OUTPUT: %s",
            dump_json({"session_id": session_id, "reply": reply}),
        )
        return reply
