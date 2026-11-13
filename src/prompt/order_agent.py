"""System prompt for LLM order extraction and deterministic Vietnamese order response formatter."""

import re

from src.schema.order import MenuMatch, OrderCalculation, OrderStatus

ORDER_EXTRACTION_SYSTEM_PROMPT = """Bạn là bộ trích xuất đơn hàng cho quán cà phê Việt Nam.
Hãy phân tích câu nói của khách hàng và trả về duy nhất một JSON object theo đúng cấu trúc sau (không kèm giải thích):

{
  "intent": "add" | "remove" | "update" | "confirm" | "cancel",
  "items": [
    {
      "name": "tên món khách gọi (bỏ từ 'ly', 'cốc', 'cái')",
      "size": "S" | "M" | "L",
      "quantity": 1,
      "note": "ghi chú thêm như ít đá, ít ngọt, không đường (để rỗng nếu không có)",
      "action": "add" | "remove" | "update"
    }
  ]
}

Quy tắc:
1. Nếu khách gọi món mới hoặc thêm món -> intent = "add", mỗi món có action = "add". Nếu khách không nói size thì mặc định size = "M", không nói số lượng thì mặc định quantity = 1.
2. Nếu khách đổi size hoặc số lượng món đã gọi -> intent = "update", món đó có action = "update".
3. Nếu khách muốn bỏ/xóa một món khỏi giỏ -> intent = "remove", món đó có action = "remove".
4. Nếu khách xác nhận chốt đơn ("Đúng rồi", "Ok chốt đơn", "Xác nhận", "Đồng ý", "Chốt nhé") -> intent = "confirm", items = [].
5. Nếu khách muốn hủy toàn bộ đơn hàng ("Hủy đơn", "Không đặt nữa", "Xóa hết giỏ hàng") -> intent = "cancel", items = [].
"""

_SHORT_FOLLOWUP_RE = re.compile(
    r"\b(?:đúng\s*rồi|đúng|chuẩn|ok|oke|okay|chốt|xác\s*nhận|đồng\s*ý|nhất\s*trí|hủy|huỷ|không\s*đặt)\b",
    re.IGNORECASE,
)


def build_order_extraction_system_prompt() -> str:
    return ORDER_EXTRACTION_SYSTEM_PROMPT


def is_short_order_followup(message: str) -> bool:
    """Return True if a short message looks like a confirmation or cancellation of a pending order."""
    text = message.strip()
    if not text or len(text) > 80:
        return False
    return bool(_SHORT_FOLLOWUP_RE.search(text))


def format_vnd(amount: int) -> str:
    """Format integer VND with dot thousands separator, e.g. 143000 -> '143.000đ'."""
    return f"{int(amount):,}".replace(",", ".") + "đ"


def _format_item_line(item: MenuMatch) -> str:
    size_label = "Một cỡ" if item.size == "Một cỡ" else f"Size {item.size}"
    note_suffix = f" [Ghi chú: {item.note}]" if item.note else ""
    req_clean = item.requested_name.strip().lower()
    matched_note = ""
    if req_clean and req_clean != item.name_vi.lower() and req_clean not in item.name_vi.lower():
        matched_note = f" (khớp từ '{item.requested_name}')"
    return (
        f"- {item.quantity} x {item.name_vi}{matched_note} ({size_label}): "
        f"{format_vnd(item.line_total_vnd)} ({format_vnd(item.unit_price_vnd)}/món){note_suffix}"
    )


def format_order_response(calc: OrderCalculation) -> str:
    """Render a deterministic, human-friendly Vietnamese reply for the current order state."""
    if calc.status is OrderStatus.CANCELLED:
        return "Mình đã hủy toàn bộ giỏ hàng theo yêu cầu của bạn. Khi nào muốn đặt món mới bạn cứ nhắn mình nhé!"

    if calc.status is OrderStatus.EMPTY:
        if calc.unmatched_items:
            missing = ", ".join(f"'{name}'" for name in calc.unmatched_items)
            return (
                f"Hiện tại trong menu của quán chưa tìm thấy món {missing}. "
                "Bạn vui lòng kiểm tra lại tên món hoặc nhờ mình tư vấn món tương tự nhé!"
            )
        return (
            "Giỏ hàng của bạn hiện đang trống ạ. "
            "Bạn muốn đặt món gì (kèm size S/M/L và số lượng) để mình lên đơn giúp bạn nhé!"
        )

    lines = [_format_item_line(item) for item in calc.items]
    items_block = "\n".join(lines)

    if calc.status is OrderStatus.CONFIRMED:
        return (
            "Đã chốt đơn thành công! Chi tiết đơn hàng của bạn:\n"
            f"{items_block}\n"
            f"Tổng thanh toán: {format_vnd(calc.total_vnd)}.\n"
            "Cảm ơn bạn, quán đang chuẩn bị món cho bạn ngay ạ!"
        )

    # PENDING_CONFIRMATION: always ask the user to verify the matched items before confirming
    unmatched_notice = ""
    if calc.unmatched_items:
        missing = ", ".join(f"'{name}'" for name in calc.unmatched_items)
        unmatched_notice = f"\n(Lưu ý: Món {missing} hiện không có trong menu của quán nên mình chưa thêm vào giỏ)."

    return (
        "Mình đã tìm thấy các món trong menu và cập nhật giỏ hàng tạm tính của bạn:\n"
        f"{items_block}\n"
        f"Tổng tạm tính: {format_vnd(calc.total_vnd)}.{unmatched_notice}\n"
        "Bạn kiểm tra giúp mình xem các món và size đã đúng ý bạn chưa ạ? "
        "Nhắn 'Xác nhận' để mình chốt đơn hoặc báo mình nếu cần thay đổi nhé!"
    )
