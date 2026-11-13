"""Extract domain entities (Branches, Payments, Promotions) from text."""

import re

from src.rag.ingestion.entity_deduplicator import EntityDeduplicator
from src.schema.retrieval import EntityRecord

_BRANCH_KEYWORDS: list[str] = [
    "Cầu Giấy", "Nguyễn Huệ", "Tràng Tiền", "Bạch Đằng", "Trần Phú",
    "Võ Văn Tần", "Phạm Văn Đồng", "Ninh Kiều", "Landmark 81", "Hồ Gươm",
    "Phan Xích Long", "Thảo Điền",
]

_PAYMENT_KEYWORDS: dict[str, str] = {
    "momo": "Ví MoMo",
    "zalopay": "Ví ZaloPay",
    "vnpay": "VNPay QR",
    "visa": "Thẻ Visa",
    "mastercard": "Thẻ Mastercard",
    "tiền mặt": "Tiền mặt",
}

_PROMO_CODE_RE = re.compile(r"\b(HL[A-Z0-9]+)\b", re.IGNORECASE)


class EntityExtractor:
    def __init__(self, deduplicator: EntityDeduplicator | None = None) -> None:
        self.deduplicator = deduplicator or EntityDeduplicator()

    async def extract_entities(self, text: str) -> list[EntityRecord]:
        lowered = text.lower()
        found: dict[str, EntityRecord] = {}

        # 1. Match branches
        for b_name in _BRANCH_KEYWORDS:
            if b_name.lower() in lowered:
                entity = self.deduplicator.deduplicate(f"Chi nhánh {b_name}", "BRANCH")
                found[entity.canonical_name] = entity

        # 2. Match payments
        for p_key, p_name in _PAYMENT_KEYWORDS.items():
            if p_key in lowered:
                entity = self.deduplicator.deduplicate(p_name, "PAYMENT")
                found[entity.canonical_name] = entity

        # 3. Match promo voucher codes
        for match in _PROMO_CODE_RE.finditer(text):
            code = match.group(1).upper()
            entity = self.deduplicator.deduplicate(f"Mã khuyến mãi {code}", "PROMOTION")
            found[entity.canonical_name] = entity

        return list(found.values())
