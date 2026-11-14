"""End-to-end tests for Phase 4 OrderAgent (create_agent + @tool) confirmation workflow through DeepAgent."""

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from src.agent.deep_agent import DeepAgent
from src.agent.subagent_registry import SubAgentRegistry
from src.schema.chat import ChatRequest
from src.schema.retrieval import MenuItemRecord
from src.schema.router import RouterAction, RouterDecision
from src.services.order_service import OrderService
from src.subagents.order_agent import OrderAgent


class FakeRouter:
    def __init__(self, decisions: list[RouterAction]):
        self._decisions = list(decisions)
        self._idx = 0

    async def route(self, message: str) -> RouterDecision:
        action = self._decisions[self._idx]
        self._idx += 1
        return RouterDecision(action=action, confidence=0.92)


class FakeToolCallingChatModel(GenericFakeChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


class FakeMenuRepo:
    def __init__(self):
        self.items = {
            "M001": MenuItemRecord(
                item_id="M001",
                name_vi="Phin Sữa Đá",
                name_en="Iced Vietnamese Milk Coffee",
                category="Cà phê",
                category_en="Coffee",
                price_s=33000,
                price_m=39000,
                price_l=49000,
                sizes=["S", "M", "L"],
            ),
            "M077": MenuItemRecord(
                item_id="M077",
                name_vi="Bánh Tiramisu",
                name_en="Tiramisu",
                category="Bánh ngọt",
                category_en="Cakes & Pastries",
                price_s=None,
                price_m=45000,
                price_l=None,
                sizes=["Một cỡ"],
            ),
        }

    async def find_menu_item_by_text(self, query: str) -> MenuItemRecord | None:
        q = query.strip().lower()
        for item in self.items.values():
            if q == item.name_vi.lower() or q in item.name_vi.lower() or item.name_vi.lower() in q:
                return item
        return None

    async def find_menu_item_by_vector(self, embedding: list[float], min_score: float = 0.82, top_k: int = 3):
        return None


async def test_full_order_add_update_and_confirm_flow():
    router = FakeRouter([
        RouterAction.ORDER,
        RouterAction.ORDER,
        RouterAction.IGNORE,  # Short confirmation "Đúng rồi, chốt nhé" that Jev might mark IGNORE
    ])
    llm = FakeToolCallingChatModel(
        messages=iter([
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "add_order_items",
                        "args": {
                            "items": [
                                {"name": "cà phê sữa đá", "size": "L", "quantity": 2, "note": "ít đá"},
                                {"name": "bánh tiramisu", "size": "M", "quantity": 1},
                            ]
                        },
                        "id": "call_1",
                    }
                ],
            ),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "update_order_items",
                        "args": {
                            "items": [
                                {"name": "Phin Sữa Đá", "size": "M", "quantity": 2},
                            ]
                        },
                        "id": "call_2",
                    }
                ],
            ),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "confirm_order",
                        "args": {},
                        "id": "call_3",
                    }
                ],
            ),
        ])
    )

    order_service = OrderService(repository=FakeMenuRepo())
    order_agent = OrderAgent(
        model_client=llm,
        order_service=order_service,
        model="google/gemini-2.5-flash",
    )
    registry = SubAgentRegistry.with_default_stubs()
    registry.register(order_agent)
    deep_agent = DeepAgent(router=router, registry=registry)

    # Turn 1: Add items -> must ask for confirmation, NOT finalize yet
    res1 = await deep_agent.handle(
        ChatRequest(
            session_id="sess-order-1",
            message="Cho mình 2 ly cà phê sữa đá size L ít đá và 1 bánh tiramisu",
        )
    )
    assert res1.action is RouterAction.ORDER
    assert "Phin Sữa Đá" in res1.reply
    assert "98.000đ" in res1.reply
    assert "Bánh Tiramisu" in res1.reply
    assert "45.000đ" in res1.reply
    assert "143.000đ" in res1.reply
    assert "Xác nhận" in res1.reply or "đúng ý bạn chưa" in res1.reply
    assert order_service.has_pending_order("sess-order-1") is True

    # Turn 2: Modify size from L to M -> recalculates 78.000 + 45.000 = 123.000đ and asks again
    res2 = await deep_agent.handle(
        ChatRequest(
            session_id="sess-order-1",
            message="Đổi Phin Sữa Đá sang size M giúp mình",
        )
    )
    assert res2.action is RouterAction.ORDER
    assert "78.000đ" in res2.reply
    assert "123.000đ" in res2.reply
    assert order_service.has_pending_order("sess-order-1") is True

    # Turn 3: Short confirmation "Đúng rồi, chốt nhé" -> DeepAgent overrides IGNORE -> confirms order
    res3 = await deep_agent.handle(
        ChatRequest(
            session_id="sess-order-1",
            message="Đúng rồi, chốt nhé",
        )
    )
    assert res3.action is RouterAction.ORDER
    assert "chốt đơn thành công" in res3.reply.lower() or "xác nhận đơn hàng" in res3.reply.lower()
    assert "123.000đ" in res3.reply
    assert order_service.has_pending_order("sess-order-1") is False
