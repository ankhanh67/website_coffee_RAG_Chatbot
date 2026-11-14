"""Unit tests for SemanticCache and its integration with DeepAgent."""

from src.agent.deep_agent import DeepAgent
from src.agent.subagent_registry import SubAgentRegistry
from src.rag.cache.semantic_cache import SemanticCache, cosine_similarity
from src.schema.chat import ChatRequest
from src.schema.router import RouterAction, RouterDecision
from src.subagents.base import BaseSubAgent


class FakeEmbeddingProvider:
    def __init__(self, vectors: dict[str, list[float]]) -> None:
        self._vectors = vectors
        self.calls: list[str] = []

    async def get_embedding(self, text: str) -> list[float]:
        self.calls.append(text)
        return self._vectors.get(text, [1.0, 0.0, 0.0])


class CountingSubAgent(BaseSubAgent):
    def __init__(self, action: RouterAction, reply: str) -> None:
        self.action = action
        self._reply = reply
        self.call_count = 0

    async def handle(self, message: str, session_id: str) -> str:
        self.call_count += 1
        return self._reply


class FixedRouter:
    def __init__(self, action: RouterAction) -> None:
        self._action = action

    async def route(self, message: str) -> RouterDecision:
        return RouterDecision(action=self._action, confidence=0.95)


def test_cosine_similarity_computation():
    assert round(cosine_similarity([1.0, 0.0], [1.0, 0.0]), 4) == 1.0
    assert round(cosine_similarity([1.0, 0.0], [0.0, 1.0]), 4) == 0.0
    assert cosine_similarity([], [1.0]) == 0.0


async def test_semantic_cache_lookup_and_store_for_faq_and_never_order():
    embedder = FakeEmbeddingProvider({
        "Quán mở cửa mấy giờ?": [0.98, 0.20, 0.0],
        "Mấy giờ quán mở cửa vậy?": [0.97, 0.22, 0.0],
        "Cho mình 1 Bạc Xỉu": [0.10, 0.95, 0.0],
    })
    cache = SemanticCache(embeddings_client=embedder, similarity_threshold=0.92)

    # ORDER must never be stored
    await cache.store("Cho mình 1 Bạc Xỉu", RouterAction.ORDER, "Giỏ hàng tạm tính...")
    assert await cache.lookup("Cho mình 1 Bạc Xỉu") is None

    # FAQ is stored and matched semantically
    await cache.store("Quán mở cửa mấy giờ?", RouterAction.FAQ, "Quán mở cửa từ 07:00 đến 22:00.")
    hit = await cache.lookup("Mấy giờ quán mở cửa vậy?")
    assert hit is not None
    entry, score = hit
    assert entry.action is RouterAction.FAQ
    assert "07:00" in entry.reply
    assert score >= 0.92


async def test_deep_agent_returns_cached_faq_without_reinvoking_subagent():
    embedder = FakeEmbeddingProvider({
        "Quán có chỗ đỗ ô tô không?": [0.95, 0.31, 0.0],
        "Ở quán có chỗ gửi ô tô không?": [0.94, 0.33, 0.0],
    })
    cache = SemanticCache(embeddings_client=embedder, similarity_threshold=0.92)
    faq_subagent = CountingSubAgent(RouterAction.FAQ, "Có chỗ đỗ ô tô tại 8 chi nhánh.")

    registry = SubAgentRegistry.with_default_stubs()
    registry.register(faq_subagent)

    agent = DeepAgent(
        router=FixedRouter(RouterAction.FAQ),
        registry=registry,
        semantic_cache=cache,
    )

    # First call executes FAQ subagent and populates cache
    res1 = await agent.handle(
        ChatRequest(session_id="s1", message="Quán có chỗ đỗ ô tô không?")
    )
    assert res1.action is RouterAction.FAQ
    assert faq_subagent.call_count == 1

    # Second semantically similar call hits SemanticCache without calling FAQ subagent again
    res2 = await agent.handle(
        ChatRequest(session_id="s2", message="Ở quán có chỗ gửi ô tô không?")
    )
    assert res2.action is RouterAction.FAQ
    assert res2.reply == "Có chỗ đỗ ô tô tại 8 chi nhánh."
    assert faq_subagent.call_count == 1
