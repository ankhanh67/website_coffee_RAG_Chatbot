"""Application settings loaded from environment / .env via pydantic-settings."""

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM API
    llm_api_key: SecretStr
    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_decisions_url: str = "https://openrouter.ai/api/alpha/decisions"
    llm_router_model: str = "~typesafe/jev-latest"  # Jev (System One) via OpenRouter Decisions API
    llm_generator_model: str = "google/gemini-2.5-flash"
    embedding_model: str = "gemini-embedding-001"
    vector_dimensions: int = Field(768, gt=0)

    # Neo4j Aura
    neo4j_uri: str
    neo4j_username: str = "neo4j"
    neo4j_password: SecretStr

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Timeouts & thresholds
    llm_timeout_seconds: float = Field(30.0, gt=0)
    llm_max_retries: int = Field(2, ge=0)
    cache_similarity_threshold: float = Field(0.90, ge=0.0, le=1.0)
    router_confidence_threshold: float = Field(0.5, ge=0.0, le=1.0)


@lru_cache
def get_settings() -> Settings:
    return Settings()

