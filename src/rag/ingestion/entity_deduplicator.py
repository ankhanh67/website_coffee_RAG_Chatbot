"""Entity deduplication using token Jaccard similarity and core canonical entity mapping."""

import re
import unicodedata

from src.schema.retrieval import EntityRecord

_PREFIX_RE = re.compile(r"^(?:chi\s*nhánh|quán|cửa\s*hàng|highlands\s*coffee|highlands)\s+", re.IGNORECASE)


def _tokenize(text: str) -> set[str]:
    norm = unicodedata.normalize("NFC", text).strip().lower()
    cleaned = _PREFIX_RE.sub("", norm).strip()
    tokens = re.findall(r"\w+", cleaned)
    return set(tokens)


def jaccard_token_similarity(a: str, b: str) -> float:
    """Compute token-level Jaccard similarity between two entity strings."""
    tokens_a = _tokenize(a)
    tokens_b = _tokenize(b)
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


DEFAULT_CORE_ENTITIES: list[EntityRecord] = [
    # 12 Branches
    EntityRecord(name="Chi nhánh Cầu Giấy", entity_type="BRANCH", canonical_name="branch_cau_giay"),
    EntityRecord(name="Chi nhánh Nguyễn Huệ", entity_type="BRANCH", canonical_name="branch_nguyen_hue"),
    EntityRecord(name="Chi nhánh Tràng Tiền", entity_type="BRANCH", canonical_name="branch_trang_tien"),
    EntityRecord(name="Chi nhánh Bạch Đằng", entity_type="BRANCH", canonical_name="branch_bach_dang"),
    EntityRecord(name="Chi nhánh Trần Phú", entity_type="BRANCH", canonical_name="branch_tran_phu"),
    EntityRecord(name="Chi nhánh Võ Văn Tần", entity_type="BRANCH", canonical_name="branch_vo_van_tan"),
    EntityRecord(name="Chi nhánh Phạm Văn Đồng", entity_type="BRANCH", canonical_name="branch_pham_van_dong"),
    EntityRecord(name="Chi nhánh Ninh Kiều", entity_type="BRANCH", canonical_name="branch_ninh_kieu"),
    EntityRecord(name="Chi nhánh Landmark 81", entity_type="BRANCH", canonical_name="branch_landmark_81"),
    EntityRecord(name="Chi nhánh Hồ Gươm", entity_type="BRANCH", canonical_name="branch_ho_guom"),
    EntityRecord(name="Chi nhánh Phan Xích Long", entity_type="BRANCH", canonical_name="branch_phan_xich_long"),
    EntityRecord(name="Chi nhánh Thảo Điền", entity_type="BRANCH", canonical_name="branch_thao_dien"),
    # Payment methods
    EntityRecord(name="Ví MoMo", entity_type="PAYMENT", canonical_name="payment_momo"),
    EntityRecord(name="Ví ZaloPay", entity_type="PAYMENT", canonical_name="payment_zalopay"),
    EntityRecord(name="VNPay QR", entity_type="PAYMENT", canonical_name="payment_vnpay"),
    EntityRecord(name="Thẻ Visa", entity_type="PAYMENT", canonical_name="payment_visa"),
    EntityRecord(name="Thẻ Mastercard", entity_type="PAYMENT", canonical_name="payment_mastercard"),
    EntityRecord(name="Tiền mặt", entity_type="PAYMENT", canonical_name="payment_cash"),
]


class EntityDeduplicator:
    def __init__(self, threshold: float = 0.50) -> None:
        self._threshold = threshold
        self._entities: list[EntityRecord] = []
        for entity in DEFAULT_CORE_ENTITIES:
            self.register_canonical(entity)

    def register_canonical(self, entity: EntityRecord) -> None:
        self._entities.append(entity)

    def deduplicate(self, raw_name: str, entity_type: str) -> EntityRecord:
        cleaned = raw_name.strip()
        best_match: EntityRecord | None = None
        best_sim = 0.0

        for entity in self._entities:
            if entity.entity_type != entity_type:
                continue
            sim = jaccard_token_similarity(cleaned, entity.name)
            if sim > best_sim:
                best_sim = sim
                best_match = entity

        if best_match is not None and best_sim >= self._threshold:
            return EntityRecord(
                name=best_match.name,
                entity_type=entity_type,
                canonical_name=best_match.canonical_name,
            )

        slug = re.sub(r"\W+", "_", cleaned.lower()).strip("_")
        canonical_name = f"{entity_type.lower()}_{slug}"
        new_entity = EntityRecord(
            name=cleaned,
            entity_type=entity_type,
            canonical_name=canonical_name,
        )
        self._entities.append(new_entity)
        return new_entity
