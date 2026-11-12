"""Dependency injection providers for FastAPI routes."""

from functools import lru_cache

from src.agent.deep_agent import DeepAgent
from src.agent.router import Router
from src.agent.subagent_registry import SubAgentRegistry
from src.config import get_settings
from src.infrastructure.model_client import ModelClient
from src.services.chat_service import ChatService


@lru_cache
def get_model_client() -> ModelClient:
    s = get_settings()
    return ModelClient(
        api_key=s.llm_api_key.get_secret_value(),
        decisions_url=s.llm_decisions_url,
        timeout_seconds=s.llm_timeout_seconds,
        max_retries=s.llm_max_retries,
    )


@lru_cache
def get_chat_service() -> ChatService:
    s = get_settings()
    router = Router(
        client=get_model_client(),
        model=s.llm_router_model,
        confidence_threshold=s.router_confidence_threshold,
    )
    deep_agent = DeepAgent(router=router, registry=SubAgentRegistry.with_default_stubs())
    return ChatService(deep_agent=deep_agent)
