"""Dependency injection providers for FastAPI routes."""

from functools import lru_cache

from src.agent.deep_agent import DeepAgent
from src.agent.router import Router
from src.agent.subagent_registry import SubAgentRegistry
from src.config import get_settings
from src.infrastructure.model_client import ModelClient
from src.rag.embeddings import EmbeddingsClient
from src.rag.graph.client import Neo4jClient
from src.rag.graph.repository import Neo4jRepository
from src.services.chat_service import ChatService
from src.services.order_service import OrderService
from src.subagents.order_agent import OrderAgent


@lru_cache
def get_model_client() -> ModelClient:
    s = get_settings()
    return ModelClient(
        api_key=s.llm_api_key.get_secret_value(),
        decisions_url=s.llm_decisions_url,
        base_url=s.llm_base_url,
        timeout_seconds=s.llm_timeout_seconds,
        max_retries=s.llm_max_retries,
    )


@lru_cache
def get_neo4j_client() -> Neo4jClient:
    s = get_settings()
    return Neo4jClient(
        uri=s.neo4j_uri,
        username=s.neo4j_username,
        password=s.neo4j_password.get_secret_value(),
        database=s.neo4j_database,
    )


@lru_cache
def get_neo4j_repository() -> Neo4jRepository:
    return Neo4jRepository(client=get_neo4j_client())


@lru_cache
def get_embeddings_client() -> EmbeddingsClient:
    s = get_settings()
    model_name = s.embedding_model
    if "/" not in model_name:
        model_name = f"google/{model_name}"
    return EmbeddingsClient(
        api_key=s.llm_api_key.get_secret_value(),
        base_url=s.llm_base_url,
        model=model_name,
        dimensions=s.vector_dimensions,
    )


@lru_cache
def get_order_service() -> OrderService:
    return OrderService(
        repository=get_neo4j_repository(),
        embeddings_client=get_embeddings_client(),
    )


@lru_cache
def get_chat_service() -> ChatService:
    s = get_settings()
    model_client = get_model_client()
    router = Router(
        client=model_client,
        model=s.llm_router_model,
        confidence_threshold=s.router_confidence_threshold,
    )
    registry = SubAgentRegistry.with_default_stubs()
    registry.register(
        OrderAgent(
            model_client=model_client,
            order_service=get_order_service(),
            model=s.llm_generator_model,
        )
    )
    deep_agent = DeepAgent(
        router=router,
        registry=registry,
        model_client=model_client,
        model=s.llm_generator_model,
    )
    return ChatService(deep_agent=deep_agent)
