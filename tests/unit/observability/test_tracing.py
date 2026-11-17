"""Unit tests for Langfuse tracing utilities (`src/observability/tracing.py`)."""

from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from src.config import Settings
from src.observability.tracing import (
     configure_tracing,
    get_langchain_callbacks,
    get_langfuse_client,
    is_tracing_enabled,
    shutdown_tracing,
    trace_chat_request,
    trace_observation,
)


def _make_settings(**overrides) -> Settings:
    base = {
        "llm_api_key": "k",
        "neo4j_uri": "neo4j+s://x",
        "neo4j_password": "p",
    }
    return Settings(_env_file=None, **{**base, **overrides})


def test_tracing_disabled_when_keys_missing():
    shutdown_tracing()
    settings = _make_settings(langfuse_public_key=None, langfuse_secret_key=None)
    client = configure_tracing(settings)

    assert client is None
    assert not is_tracing_enabled()
    assert get_langfuse_client() is None
    assert get_langchain_callbacks() == []

    # No-op context managers should still work and expose .update()
    with trace_chat_request(session_id="s1", message="hi", job_id="j1") as root:
        root.update(output={"reply": "hello"})
        with trace_observation("router.route", as_type="generation", input={"q": "hi"}) as obs:
            obs.update(output={"action": "ignore"})


def test_tracing_creates_hierarchical_spans_with_in_memory_exporter():
    shutdown_tracing()
    exporter = InMemorySpanExporter()
    settings = _make_settings(
        langfuse_public_key="pk-lf-test-unit",
        langfuse_secret_key="sk-lf-test-unit",
        langfuse_tracing_enabled=True,
    )
    client = configure_tracing(settings, span_exporter=exporter)

    assert client is not None
    assert is_tracing_enabled()
    callbacks = get_langchain_callbacks()
    assert len(callbacks) == 1

    with trace_chat_request(
        session_id="sess-coffee-01",
        message="Cho mình 1 bạc xỉu",
        job_id="job-123",
    ) as root_span:
        with trace_observation(
            name="jev_router",
            as_type="generation",
            model="~typesafe/jev-latest",
            input={"message": "Cho mình 1 bạc xỉu"},
        ) as router_span:
            router_span.update(
                output={"action": "order", "confidence": 0.96},
                usage_details={"input": 25, "output": 5},
            )
        root_span.update(output={"action": "order", "reply": "Dạ mình đã thêm 1 Bạc xỉu"})

    client.flush()
    spans = exporter.get_finished_spans()
    span_by_name = {s.name: s for s in spans}

    assert "chat_request" in span_by_name
    assert "jev_router" in span_by_name

    root = span_by_name["chat_request"]
    child = span_by_name["jev_router"]

    assert child.parent is not None
    assert child.parent.span_id == root.context.span_id
    assert child.context.trace_id == root.context.trace_id
    assert root.attributes.get("session.id") == "sess-coffee-01" or (
        root.attributes.get("langfuse.trace.session_id") == "sess-coffee-01"
    )

    shutdown_tracing()
    assert not is_tracing_enabled()


async def test_full_chat_pipeline_emits_unified_langfuse_trace():
    import httpx2 as httpx

    from src.agent.deep_agent import DeepAgent
    from src.agent.router import Router
    from src.agent.subagent_registry import SubAgentRegistry
    from src.infrastructure.model_client import ModelClient
    from src.rag.cache.semantic_cache import SemanticCache
    from src.rag.retrieval.hybrid_search import HybridRetriever
    from src.schema.chat import ChatRequest
    from src.schema.retrieval import ChunkRecord
    from src.schema.router import RouterAction
    from src.services.chat_service import ChatService
    from src.subagents.base import BaseSubAgent

    shutdown_tracing()
    exporter = InMemorySpanExporter()
    settings = _make_settings(
        langfuse_public_key="pk-lf-pipeline",
        langfuse_secret_key="sk-lf-pipeline",
        langfuse_tracing_enabled=True,
    )
    client = configure_tracing(settings, span_exporter=exporter)
    assert client is not None

    def mock_jev_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "answers": {
                    "route": {
                        "type": "choice",
                        "choice": "faq",
                        "confidence": 0.94,
                        "probabilities": {"faq": 0.94},
                    }
                },
                "usage": {"prompt_tokens": 30, "completion_tokens": 4, "total_tokens": 34},
            },
        )

    model_client = ModelClient(
        api_key="test-key",
        decisions_url="https://example.test/decisions",
        transport=httpx.MockTransport(mock_jev_handler),
    )
    router = Router(client=model_client, model="~typesafe/jev-latest", confidence_threshold=0.5)

    class DummyEmbeddings:
        async def get_embedding(self, text: str) -> list[float]:
            return [1.0, 0.0, 0.0]

    class DummyRepo:
        async def search_chunks_by_vector(self, embedding, top_k, min_score):
            return [
                (
                    ChunkRecord(
                        chunk_id="faq-01",
                        source="faq",
                        title="Giờ mở cửa",
                        text="Mở cửa 7h - 22h",
                    ),
                    0.92,
                )
            ]

        async def search_menu_items_by_vector(self, embedding, top_k, min_score):
            return []

        async def expand_chunks_next(self, chunk_ids):
            return []

        async def expand_chunks_by_entities(self, chunk_ids, limit=10):
            return []

        async def expand_chunks_by_title_mention(self, chunk_ids, limit=10):
            return []

    class DummyFAQSubAgent(BaseSubAgent):
        action = RouterAction.FAQ

        def __init__(self, retriever: HybridRetriever) -> None:
            self._retriever = retriever

        async def handle(self, message: str, session_id: str) -> str:
            res = await self._retriever.retrieve(query=message, top_k=2)
            return f"Quán mở cửa từ 7h sáng ({len(res.items)} nguồn)."

    retriever = HybridRetriever(repository=DummyRepo(), embeddings_client=DummyEmbeddings())
    registry = SubAgentRegistry()
    registry.register(DummyFAQSubAgent(retriever))
    cache = SemanticCache(embeddings_client=DummyEmbeddings(), similarity_threshold=0.90)
    deep_agent = DeepAgent(
        router=router,
        registry=registry,
        model_client=None,
        semantic_cache=cache,
    )
    chat_service = ChatService(deep_agent=deep_agent)

    resp = await chat_service.chat(
        ChatRequest(session_id="sess-e2e-trace", message="Quán mở cửa mấy giờ?")
    )
    assert resp.action is RouterAction.FAQ
    assert "7h sáng" in resp.reply

    client.flush()
    spans = exporter.get_finished_spans()
    span_names = {s.name for s in spans}

    assert "chat_request" in span_names
    assert "DeepAgent.handle" in span_names
    assert "Router.route" in span_names
    assert "ModelClient.decide" in span_names
    assert "SemanticCache.lookup" in span_names
    assert "SemanticCache.store" in span_names
    assert "HybridRetriever.retrieve" in span_names

    # All spans in this turn share the exact same root trace_id
    trace_ids = {s.context.trace_id for s in spans}
    assert len(trace_ids) == 1

    await model_client.aclose()
    shutdown_tracing()
