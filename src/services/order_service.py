"""Deterministic OrderService: menu matching (Text + Vector fallback), pricing, and cart state machine."""

import logging
import re
from typing import Literal, Protocol

from src.observability.logging import dump_json
from src.schema.order import (
    MenuMatch,
    OrderCalculation,
    OrderExtraction,
    OrderIntentType,
    OrderItemInput,
    OrderStatus,
)
from src.schema.retrieval import MenuItemRecord

logger = logging.getLogger(__name__)

_LEADING_CLASSIFIER_RE = re.compile(
    r"^(?:cho\s+mình|lấy|gọi|thêm|đổi|bỏ|xóa)?\s*(?:\d+\s*)?(?:ly|cốc|phần|cái|chiếc|món|suất|chai|hộp)\s+",
    re.IGNORECASE,
)

COMMON_MENU_ALIASES: dict[str, str] = {
    "cà phê sữa đá": "Phin Sữa Đá",
    "cafe sữa đá": "Phin Sữa Đá",
    "cf sữa đá": "Phin Sữa Đá",
    "cà phê sữa": "Phin Sữa Đá",
    "cà phê sữa nóng": "Phin Sữa Nóng",
    "cafe sữa nóng": "Phin Sữa Nóng",
    "cà phê đen đá": "Phin Đen Đá",
    "cafe đen đá": "Phin Đen Đá",
    "đen đá": "Phin Đen Đá",
    "cà phê đen": "Phin Đen Đá",
    "cà phê đen nóng": "Phin Đen Nóng",
    "cafe đen nóng": "Phin Đen Nóng",
    "đen nóng": "Phin Đen Nóng",
    "bạc xỉu đá": "Bạc Xỉu",
    "bạc xỉu nóng": "Bạc Xỉu",
    "bạc sỉu": "Bạc Xỉu",
    "trà đào": "Trà Đào Cam Sả",
    "matcha đá xay": "Freeze Trà Xanh",
}


class MenuLookupRepository(Protocol):
    async def find_menu_item_by_text(self, query: str) -> MenuItemRecord | None: ...
    async def find_menu_item_by_vector(
        self,
        embedding: list[float],
        min_score: float = 0.82,
        top_k: int = 3,
    ) -> tuple[MenuItemRecord, float] | None: ...


class EmbeddingProvider(Protocol):
    async def get_embedding(self, text: str) -> list[float]: ...


def normalize_item_query(raw_name: str) -> str:
    cleaned = _LEADING_CLASSIFIER_RE.sub("", raw_name.strip()).strip()
    lowered = cleaned.lower()
    if lowered in COMMON_MENU_ALIASES:
        return COMMON_MENU_ALIASES[lowered]
    return cleaned


class OrderService:
    def __init__(
        self,
        repository: MenuLookupRepository,
        embeddings_client: EmbeddingProvider | None = None,
        vector_min_score: float = 0.82,
    ) -> None:
        self._repository = repository
        self._embeddings = embeddings_client
        self._vector_min_score = vector_min_score
        self._carts: dict[str, list[MenuMatch]] = {}

    def has_pending_order(self, session_id: str) -> bool:
        return bool(self._carts.get(session_id))

    def get_cart(self, session_id: str) -> list[MenuMatch]:
        return list(self._carts.get(session_id, []))

    async def match_menu_item(self, name: str) -> MenuItemRecord | None:
        query = normalize_item_query(name)
        if not query:
            return None

        record = await self._repository.find_menu_item_by_text(query)
        if record is not None:
            return record

        if self._embeddings is not None:
            vec = await self._embeddings.get_embedding(query)
            vec_match = await self._repository.find_menu_item_by_vector(
                vec, min_score=self._vector_min_score
            )
            if vec_match is not None:
                return vec_match[0]

        return None

    @staticmethod
    def resolve_size_and_price(
        record: MenuItemRecord,
        requested_size: Literal["S", "M", "L"],
    ) -> tuple[Literal["S", "M", "L", "Một cỡ"], int]:
        is_single_size = record.sizes == ["Một cỡ"] or (
            record.price_s is None and record.price_l is None
        )
        if is_single_size:
            return "Một cỡ", int(record.price_m or 0)

        price_by_size: dict[str, int | None] = {
            "S": record.price_s,
            "M": record.price_m,
            "L": record.price_l,
        }
        chosen_price = price_by_size.get(requested_size)
        if chosen_price is not None:
            return requested_size, int(chosen_price)

        fallback_price = record.price_m or record.price_s or record.price_l or 0
        return "M", int(fallback_price)

    @staticmethod
    def _calculate_totals(
        items: list[MenuMatch],
        status: OrderStatus,
        unmatched_items: list[str] | None = None,
        message_hint: str = "",
    ) -> OrderCalculation:
        subtotal = sum(item.line_total_vnd for item in items)
        return OrderCalculation(
            status=status,
            items=list(items),
            subtotal_vnd=subtotal,
            discount_vnd=0,
            total_vnd=subtotal,
            unmatched_items=list(unmatched_items or []),
            message_hint=message_hint,
        )

    async def process_extraction(
        self,
        session_id: str,
        extraction: OrderExtraction,
    ) -> OrderCalculation:
        logger.info(
            "STAGE OrderService.process_extraction INPUT: %s",
            dump_json({"session_id": session_id, "extraction": extraction.model_dump(mode="json")}),
        )
        cart = self._carts.setdefault(session_id, [])

        if extraction.intent is OrderIntentType.CANCEL and not extraction.items:
            self._carts.pop(session_id, None)
            calc = self._calculate_totals([], OrderStatus.CANCELLED, message_hint="cancelled")
            logger.info("STAGE OrderService.process_extraction OUTPUT: %s", dump_json(calc.model_dump(mode="json")))
            return calc

        if extraction.intent in (OrderIntentType.VIEW, OrderIntentType.UNKNOWN) and not extraction.items:
            if not cart:
                calc = self._calculate_totals([], OrderStatus.EMPTY, message_hint="view_empty")
            else:
                calc = self._calculate_totals(cart, OrderStatus.PENDING_CONFIRMATION, message_hint="view")
            logger.info("STAGE OrderService.process_extraction OUTPUT: %s", dump_json(calc.model_dump(mode="json")))
            return calc

        if extraction.intent is OrderIntentType.CONFIRM and not extraction.items:
            if not cart:
                calc = self._calculate_totals([], OrderStatus.EMPTY, message_hint="confirm_empty")
            else:
                confirmed_items = list(cart)
                self._carts.pop(session_id, None)
                calc = self._calculate_totals(
                    confirmed_items,
                    OrderStatus.CONFIRMED,
                    message_hint="confirmed",
                )
            logger.info("STAGE OrderService.process_extraction OUTPUT: %s", dump_json(calc.model_dump(mode="json")))
            return calc

        unmatched: list[str] = []
        for item_input in extraction.items:
            item_action = (
                item_input.action
                if extraction.intent is OrderIntentType.ADD
                else extraction.intent
            )
            await self._apply_item_action(cart, item_input, item_action, unmatched)

        if not cart:
            self._carts.pop(session_id, None)
            status = OrderStatus.EMPTY
        else:
            status = OrderStatus.PENDING_CONFIRMATION

        calc = self._calculate_totals(
            cart,
            status=status,
            unmatched_items=unmatched,
            message_hint=extraction.intent.value,
        )
        logger.info("STAGE OrderService.process_extraction OUTPUT: %s", dump_json(calc.model_dump(mode="json")))
        return calc

    async def _apply_item_action(
        self,
        cart: list[MenuMatch],
        item_input: OrderItemInput,
        action: OrderIntentType,
        unmatched: list[str],
    ) -> None:
        record = await self.match_menu_item(item_input.name)
        if record is None:
            if action is OrderIntentType.REMOVE:
                # Try removing by raw name substring in current cart
                q = item_input.name.strip().lower()
                cart[:] = [m for m in cart if q not in m.name_vi.lower()]
                return
            unmatched.append(item_input.name)
            return

        if action is OrderIntentType.REMOVE:
            cart[:] = [m for m in cart if m.item_id != record.item_id]
            return

        resolved_size, unit_price = self.resolve_size_and_price(record, item_input.size)

        if action is OrderIntentType.UPDATE:
            for idx, existing in enumerate(cart):
                if existing.item_id == record.item_id:
                    cart[idx] = MenuMatch(
                        item_id=record.item_id,
                        name_vi=record.name_vi,
                        requested_name=item_input.name,
                        size=resolved_size,
                        unit_price_vnd=unit_price,
                        quantity=item_input.quantity,
                        note=item_input.note or existing.note,
                    )
                    return

        # Default: ADD (merge if same item_id and resolved_size already in cart)
        for idx, existing in enumerate(cart):
            if existing.item_id == record.item_id and existing.size == resolved_size:
                cart[idx] = MenuMatch(
                    item_id=existing.item_id,
                    name_vi=existing.name_vi,
                    requested_name=item_input.name,
                    size=existing.size,
                    unit_price_vnd=existing.unit_price_vnd,
                    quantity=existing.quantity + item_input.quantity,
                    note=item_input.note or existing.note,
                )
                return

        cart.append(
            MenuMatch(
                item_id=record.item_id,
                name_vi=record.name_vi,
                requested_name=item_input.name,
                size=resolved_size,
                unit_price_vnd=unit_price,
                quantity=item_input.quantity,
                note=item_input.note,
            )
        )

