"""Reranker combining Vector similarity, Graph hop confirmation, and lexical overlap."""

import unicodedata

from src.schema.retrieval import RetrievedItem


def _strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.replace("đ", "d").replace("Đ", "D"))
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def _extract_tokens(text: str) -> set[str]:
    normalized = _strip_accents(text).lower()
    cleaned = "".join(ch if ch.isalnum() else " " for ch in normalized)
    raw_tokens = [tok for tok in cleaned.split() if len(tok) >= 2]
    tokens = set(raw_tokens)
    # Include adjacent joined token pairs so ASCII 'hanoi' matches 'ha noi' ('Hà Nội')
    for i in range(len(raw_tokens) - 1):
        tokens.add(raw_tokens[i] + raw_tokens[i + 1])
    return tokens


def compute_lexical_overlap(query: str, document_text: str) -> float:
    """Compute fraction of query tokens present in the candidate document text."""
    q_tokens = _extract_tokens(query)
    if not q_tokens:
        return 0.0
    d_tokens = _extract_tokens(document_text)
    if not d_tokens:
        return 0.0
    return len(q_tokens & d_tokens) / len(q_tokens)


class HybridReranker:
    def __init__(
        self,
        lexical_weight: float = 0.08,
        multi_source_bonus: float = 0.03,
        min_score: float = 0.65,
        max_per_faq_topic: int = 2,
    ) -> None:
        self._lexical_weight = lexical_weight
        self._multi_source_bonus = multi_source_bonus
        self._min_score = min_score
        self._max_per_faq_topic = max_per_faq_topic

    def rerank(
        self,
        query: str,
        vector_items: list[RetrievedItem],
        graph_items: list[RetrievedItem],
        top_k: int = 5,
    ) -> list[RetrievedItem]:
        """Deduplicate, score-fuse, diversify FAQ topics, and rank Vector + Graph candidate items."""
        merged: dict[str, RetrievedItem] = {}
        seen_in_both: set[str] = set()

        for item in vector_items:
            existing = merged.get(item.node_id)
            if existing is None or item.score > existing.score:
                merged[item.node_id] = item.model_copy(deep=True)

        for item in graph_items:
            existing = merged.get(item.node_id)
            if existing is not None:
                seen_in_both.add(item.node_id)
                if item.score > existing.score:
                    merged[item.node_id] = item.model_copy(deep=True)
            else:
                merged[item.node_id] = item.model_copy(deep=True)

        scored_items: list[RetrievedItem] = []
        for node_id, item in merged.items():
            overlap = compute_lexical_overlap(query, f"{item.title} {item.text}")
            bonus = self._multi_source_bonus if node_id in seen_in_both else 0.0
            final_score = round(min(1.0, item.score + self._lexical_weight * overlap + bonus), 4)
            if final_score >= self._min_score:
                scored_items.append(item.model_copy(update={"score": final_score}))

        scored_items.sort(key=lambda x: x.score, reverse=True)

        diversified: list[RetrievedItem] = []
        topic_counts: dict[str, int] = {}
        for item in scored_items:
            if item.source_type == "faq":
                topic_id = str(item.metadata.get("topic_id") or "")
                if topic_id:
                    count = topic_counts.get(topic_id, 0)
                    if count >= self._max_per_faq_topic:
                        continue
                    topic_counts[topic_id] = count + 1
            diversified.append(item)

        if len(diversified) <= top_k:
            return diversified

        # Ensure balanced source coverage so document chunks and menu items are not starved by FAQ
        doc_items = [i for i in diversified if i.source_type == "document"]
        menu_items = [i for i in diversified if i.source_type == "menu"]

        min_doc_slots = min(len(doc_items), max(2, top_k // 3))
        min_menu_slots = min(len(menu_items), 2 if top_k >= 5 else 1)

        selected_docs = doc_items[:min_doc_slots]
        selected_menus = menu_items[:min_menu_slots]

        used_ids = {i.node_id for i in selected_docs} | {i.node_id for i in selected_menus}
        combined = selected_docs + selected_menus
        for item in diversified:
            if len(combined) >= top_k:
                break
            if item.node_id not in used_ids:
                combined.append(item)
                used_ids.add(item.node_id)

        combined.sort(key=lambda x: x.score, reverse=True)
        return combined
