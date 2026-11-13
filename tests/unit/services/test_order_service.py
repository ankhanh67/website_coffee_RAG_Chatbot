"""Unit tests for deterministic OrderService: menu matching, 'Một cỡ' pricing, cart state machine."""

from src.schema.order import (
    OrderExtraction,
    OrderIntentType,
    OrderItemInput,
    OrderStatus,
)
from src.schema.retrieval import MenuItemRecord
from src.services.order_service import OrderService


def make_menu_records() -> dict[str, MenuItemRecord]:
    return {
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
            temperature="iced",
            caffeine="có",
            vegan="không",
            allergens=["sữa"],
        ),
        "M005": MenuItemRecord(
            item_id="M005",
            name_vi="Bạc Xỉu",
            name_en="Bac Xiu (Milk Coffee)",
            category="Cà phê",
            category_en="Coffee",
            price_s=33000,
            price_m=39000,
            price_l=49000,
            sizes=["S", "M", "L"],
            temperature="both",
            caffeine="có",
            vegan="không",
            allergens=["sữa"],
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
            temperature="n/a",
            caffeine="có",
            vegan="không",
            allergens=["gluten", "sữa", "trứng"],
        ),
    }


class FakeMenuRepository:
    def __init__(self, records: dict[str, MenuItemRecord], vector_map: dict[str, tuple[str, float]] | None = None):
        self.records = records
        self.vector_map = vector_map or {}
        self.last_query_for_vector = ""

    async def find_menu_item_by_text(self, query: str) -> MenuItemRecord | None:
        self.last_query_for_vector = query
        q = query.strip().lower()
        for rec in self.records.values():
            n_vi = rec.name_vi.lower()
            n_en = rec.name_en.lower()
            if q == n_vi or q == n_en or q in n_vi or n_vi in q:
                return rec
        return None

    async def find_menu_item_by_vector(
        self,
        embedding: list[float],
        min_score: float = 0.82,
        top_k: int = 3,
    ) -> tuple[MenuItemRecord, float] | None:
        key = self.last_query_for_vector.lower()
        if key in self.vector_map:
            item_id, score = self.vector_map[key]
            if score >= min_score:
                return self.records[item_id], score
        return None


class FakeEmbeddingsClient:
    async def get_embedding(self, text: str) -> list[float]:
        return [0.1] * 768


async def test_add_three_size_and_single_size_items_sets_pending_confirmation():
    repo = FakeMenuRepository(make_menu_records())
    service = OrderService(repository=repo, embeddings_client=FakeEmbeddingsClient())

    extraction = OrderExtraction(
        intent=OrderIntentType.ADD,
        items=[
            OrderItemInput(name="Phin Sữa Đá", size="L", quantity=2, note="ít đá"),
            OrderItemInput(name="Bánh Tiramisu", size="L", quantity=1),
        ],
    )
    calc = await service.process_extraction("sess-1", extraction)

    assert calc.status is OrderStatus.PENDING_CONFIRMATION
    assert service.has_pending_order("sess-1") is True
    assert len(calc.items) == 2

    drink = calc.items[0]
    assert drink.item_id == "M001"
    assert drink.size == "L"
    assert drink.unit_price_vnd == 49000
    assert drink.line_total_vnd == 98000

    cake = calc.items[1]
    assert cake.item_id == "M077"
    assert cake.size == "Một cỡ"
    assert cake.unit_price_vnd == 45000
    assert cake.line_total_vnd == 45000

    assert calc.subtotal_vnd == 143000
    assert calc.total_vnd == 143000
    assert calc.unmatched_items == []


async def test_vector_fallback_and_unmatched_items():
    records = make_menu_records()
    repo = FakeMenuRepository(records, vector_map={"đồ uống đá xay kem sữa": ("M005", 0.89)})
    service = OrderService(repository=repo, embeddings_client=FakeEmbeddingsClient())

    extraction = OrderExtraction(
        intent=OrderIntentType.ADD,
        items=[
            OrderItemInput(name="cà phê sữa đá", size="M", quantity=1),
            OrderItemInput(name="đồ uống đá xay kem sữa", size="S", quantity=1),
            OrderItemInput(name="Trà Sữa Hành Lá", size="M", quantity=2),
        ],
    )
    calc = await service.process_extraction("sess-2", extraction)

    assert calc.status is OrderStatus.PENDING_CONFIRMATION
    assert len(calc.items) == 2
    assert calc.items[0].item_id == "M001"
    assert calc.items[0].unit_price_vnd == 39000
    assert calc.items[1].item_id == "M005"
    assert calc.items[1].unit_price_vnd == 33000
    assert calc.total_vnd == 72000
    assert calc.unmatched_items == ["Trà Sữa Hành Lá"]


async def test_update_remove_and_confirm_lifecycle():
    repo = FakeMenuRepository(make_menu_records())
    service = OrderService(repository=repo)

    # 1. Add 2 Phin Sữa Đá size L + 1 Bánh Tiramisu
    await service.process_extraction(
        "sess-3",
        OrderExtraction(
            intent=OrderIntentType.ADD,
            items=[
                OrderItemInput(name="Phin Sữa Đá", size="L", quantity=2),
                OrderItemInput(name="Bánh Tiramisu", size="M", quantity=1),
            ],
        ),
    )

    # 2. Update Phin Sữa Đá to size M, quantity 2 -> 2 * 39000 + 45000 = 123000
    calc_updated = await service.process_extraction(
        "sess-3",
        OrderExtraction(
            intent=OrderIntentType.UPDATE,
            items=[OrderItemInput(name="Phin Sữa Đá", size="M", quantity=2, action=OrderIntentType.UPDATE)],
        ),
    )
    assert calc_updated.status is OrderStatus.PENDING_CONFIRMATION
    assert calc_updated.total_vnd == 123000

    # 3. Remove Bánh Tiramisu -> only 2 * 39000 = 78000 left
    calc_removed = await service.process_extraction(
        "sess-3",
        OrderExtraction(
            intent=OrderIntentType.REMOVE,
            items=[OrderItemInput(name="Bánh Tiramisu", action=OrderIntentType.REMOVE)],
        ),
    )
    assert calc_removed.status is OrderStatus.PENDING_CONFIRMATION
    assert len(calc_removed.items) == 1
    assert calc_removed.total_vnd == 78000

    # 4. Confirm order -> status becomes CONFIRMED and pending cart is cleared
    calc_confirmed = await service.process_extraction(
        "sess-3",
        OrderExtraction(intent=OrderIntentType.CONFIRM),
    )
    assert calc_confirmed.status is OrderStatus.CONFIRMED
    assert calc_confirmed.total_vnd == 78000
    assert len(calc_confirmed.items) == 1
    assert service.has_pending_order("sess-3") is False


async def test_confirm_empty_cart_and_cancel_cart():
    repo = FakeMenuRepository(make_menu_records())
    service = OrderService(repository=repo)

    empty_confirm = await service.process_extraction(
        "sess-empty",
        OrderExtraction(intent=OrderIntentType.CONFIRM),
    )
    assert empty_confirm.status is OrderStatus.EMPTY
    assert empty_confirm.total_vnd == 0

    await service.process_extraction(
        "sess-cancel",
        OrderExtraction(
            intent=OrderIntentType.ADD,
            items=[OrderItemInput(name="Bạc Xỉu", size="M", quantity=1)],
        ),
    )
    assert service.has_pending_order("sess-cancel") is True

    cancelled = await service.process_extraction(
        "sess-cancel",
        OrderExtraction(intent=OrderIntentType.CANCEL),
    )
    assert cancelled.status is OrderStatus.CANCELLED
    assert cancelled.total_vnd == 0
    assert service.has_pending_order("sess-cancel") is False


async def test_view_cart_and_unknown_intent():
    repo = FakeMenuRepository(make_menu_records())
    service = OrderService(repository=repo)

    # View when empty
    view_empty = await service.process_extraction(
        "sess-view",
        OrderExtraction(intent=OrderIntentType.VIEW),
    )
    assert view_empty.status is OrderStatus.EMPTY
    assert view_empty.message_hint == "view_empty"

    # Add item
    await service.process_extraction(
        "sess-view",
        OrderExtraction(
            intent=OrderIntentType.ADD,
            items=[OrderItemInput(name="Phin Sữa Đá", size="M", quantity=2)],
        ),
    )

    # View with items
    view_populated = await service.process_extraction(
        "sess-view",
        OrderExtraction(intent=OrderIntentType.VIEW),
    )
    assert view_populated.status is OrderStatus.PENDING_CONFIRMATION
    assert view_populated.message_hint == "view"
    assert len(view_populated.items) == 1
    assert view_populated.total_vnd == 78000

    # Unknown intent also behaves like view
    view_unknown = await service.process_extraction(
        "sess-view",
        OrderExtraction(intent=OrderIntentType.UNKNOWN),
    )
    assert view_unknown.status is OrderStatus.PENDING_CONFIRMATION
    assert view_unknown.total_vnd == 78000

