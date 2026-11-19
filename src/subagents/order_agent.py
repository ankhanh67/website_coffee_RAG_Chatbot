"""OrderAgent built with `ToolEnabledSubAgent` and `@tool`."""

from collections.abc import Sequence

from langchain.tools import tool
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.checkpoint.memory import InMemorySaver

from src.agent.llm import ChatModelProvider
from src.prompt.order_agent import ORDER_AGENT_SYSTEM_PROMPT
from src.schema.order import OrderExtraction, OrderIntentType, OrderItemInput
from src.schema.router import RouterAction
from src.services.order_service import OrderService
from src.subagents.base import ToolEnabledSubAgent


def build_order_tools(order_service: OrderService, session_id: str) -> list[BaseTool]:
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


class OrderAgent(ToolEnabledSubAgent):
    action = RouterAction.ORDER
    system_prompt = ORDER_AGENT_SYSTEM_PROMPT
    default_temperature = 0.2

    def __init__(
        self,
        model_client: ChatModelProvider | BaseChatModel,
        order_service: OrderService,
        model: str = "google/gemini-2.5-flash",
        checkpointer: InMemorySaver | None = None,
    ) -> None:
        super().__init__(model_client=model_client, model=model, checkpointer=checkpointer)
        self._order_service = order_service

    def has_pending_order(self, session_id: str) -> bool:
        return self._order_service.has_pending_order(session_id)

    def _build_tools(self, session_id: str) -> Sequence[BaseTool]:
        return build_order_tools(self._order_service, session_id)
