"""Jev `choice` question used to route a customer message to one of 4 flows."""

from src.schema.router import RouterAction

ROUTE_QUESTION_KEY = "route"

ROUTER_INSTRUCTIONS = (
    "Bạn là bộ phân luồng cho chatbot của một chuỗi quán cà phê. "
    "Tin nhắn có thể bằng tiếng Việt hoặc tiếng Anh. Chọn luồng phù hợp nhất với ý định của khách."
)

ROUTER_CRITERIA: dict[RouterAction, str] = {
    RouterAction.ORDER: (
        "Khách muốn đặt món, thêm/bớt/đổi món, đổi size, số lượng, đá, đường, "
        "xác nhận hoặc hủy đơn hàng."
    ),
    RouterAction.CONSULTANT: (
        "Khách nhờ gợi ý, tư vấn chọn món theo khẩu vị, ngân sách, độ ngọt, caffeine, "
        "ăn chay hoặc dị ứng; chưa chốt món cụ thể."
    ),
    RouterAction.FAQ: (
        "Khách hỏi thông tin thực tế về quán: giờ mở cửa, chi nhánh, wifi, chỗ đậu xe, "
        "thú cưng, chính sách, khuyến mãi, thanh toán, giao hàng."
    ),
    RouterAction.IGNORE: (
        "Tin nhắn vô nghĩa, chỉ chào hỏi/xác nhận suông, cảm thán, hoặc ngoài phạm vi quán "
        "cà phê nên không cần hành động."
    ),
}


def build_router_questions() -> dict:
    return {
        ROUTE_QUESTION_KEY: {
            "type": "choice",
            "instructions": ROUTER_INSTRUCTIONS,
            "criteria": {action.value: desc for action, desc in ROUTER_CRITERIA.items()},
        }
    }

