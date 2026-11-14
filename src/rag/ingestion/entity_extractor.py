"""Extract domain entities (Branches, Payments, Promotions, Ingredients, Policies) using LLM."""

import logging
from typing import Protocol, TypeVar

from pydantic import BaseModel, Field

from src.exceptions import ModelServiceUnavailableError
from src.rag.ingestion.entity_deduplicator import EntityDeduplicator
from src.schema.retrieval import EntityRecord

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class ExtractedEntitiesResult(BaseModel):
    entities: list[EntityRecord] = Field(default_factory=list)


class LLMClientProtocol(Protocol):
    async def generate_structured(
        self,
        model: str,
        system_prompt: str,
        user_message: str,
        response_model: type[T],
        temperature: float = 0.0,
    ) -> T: ...


ENTITY_EXTRACTION_SYSTEM_PROMPT = """Bạn là trợ lý AI chuyên gia trích xuất thực thể (Named Entity Recognition) cho chuỗi quán cà phê Highlands Coffee.
Nhiệm vụ: Phân tích đoạn văn bản được cung cấp và trích xuất tất cả các thực thể quan trọng có ý nghĩa trong lĩnh vực F&B / Quán cà phê.

Các loại thực thể (entity_type):
- BRANCH: Tên chi nhánh, cơ sở quán (ví dụ: "Chi nhánh Landmark 81", "Chi nhánh Cầu Giấy", "Chi nhánh Nguyễn Huệ")
- PAYMENT: Phương thức thanh toán (ví dụ: "Ví MoMo", "Ví ZaloPay", "VNPay QR", "Tiền mặt", "Thẻ Visa")
- PROMOTION: Mã ưu đãi, voucher, chương trình khuyến mãi (ví dụ: "Mã HLCOFFEE20", "Giờ vàng 1 tặng 1")
- INGREDIENT: Loại hạt cà phê, nguyên liệu đặc trưng (ví dụ: "Hạt Arabica Cầu Đất", "Hạt Robusta", "Trà sen")
- FACILITY: Tiện ích không gian, cơ sở vật chất (ví dụ: "Chỗ đậu xe ô tô", "Phòng họp nhóm", "Khu ngoài trời", "Wifi")
- POLICY: Chính sách, quy định (ví dụ: "Chính sách thú cưng", "Quy định đổi trả", "Quy định làm lại món")
- GENERAL: Thực thể quan trọng khác đáng tra cứu.

Quy tắc xuất dữ liệu:
1. `name`: Tên thực thể rõ ràng bằng tiếng Việt.
2. `canonical_name`: Mã định danh chuẩn hóa viết thường không dấu, dùng dấu gạch dưới, bắt đầu bằng loại thực thể (ví dụ: "branch_landmark_81", "payment_momo", "promo_hlcoffee20", "facility_parking").
3. Chỉ trích xuất các thực thể thực sự xuất hiện hoặc được nói đến trong đoạn văn. Không bịa đặt.
4. Nếu đoạn văn không có thực thể cụ thể nào, trả về danh sách rỗng: {"entities": []}.
"""


class EntityExtractor:
    def __init__(
        self,
        model_client: LLMClientProtocol | None = None,
        model: str = "google/gemini-2.5-flash",
        deduplicator: EntityDeduplicator | None = None,
    ) -> None:
        self.model_client = model_client
        self.model = model
        self.deduplicator = deduplicator or EntityDeduplicator()

    async def extract_entities(self, text: str) -> list[EntityRecord]:
        if not text or not text.strip():
            return []

        if self.model_client is None:
            return []

        try:
            result = await self.model_client.generate_structured(
                model=self.model,
                system_prompt=ENTITY_EXTRACTION_SYSTEM_PROMPT,
                user_message=f"Trích xuất các thực thể từ đoạn văn sau:\n\n{text}",
                response_model=ExtractedEntitiesResult,
                temperature=0.0,
            )
        except (ModelServiceUnavailableError, ValueError, KeyError) as e:
            logger.warning("LLM entity extraction failed: %s. Returning empty list.", e)
            return []

        found: dict[str, EntityRecord] = {}
        for entity in result.entities:
            deduped = self.deduplicator.deduplicate(entity.name, entity.entity_type)
            # Use canonical_name if provided by deduped or fallback to entity's canonical_name
            final_canonical = deduped.canonical_name or entity.canonical_name
            record = EntityRecord(
                name=deduped.name,
                entity_type=entity.entity_type,
                canonical_name=final_canonical,
            )
            found[record.canonical_name] = record

        return list(found.values())
