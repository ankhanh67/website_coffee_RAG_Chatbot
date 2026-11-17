import pytest
from pydantic import ValidationError

from src.config import Settings

REQUIRED = {"llm_api_key": "k", "neo4j_uri": "neo4j+s://x", "neo4j_password": "p"}


def make(**overrides) -> Settings:
    return Settings(_env_file=None, **{**REQUIRED, **overrides})


def test_defaults_load():
    s = make()
    assert s.vector_dimensions == 768
    assert s.cache_similarity_threshold == 0.90
    assert s.llm_api_key.get_secret_value() == "k"
    assert s.langfuse_public_key is None
    assert s.langfuse_secret_key is None
    assert s.langfuse_base_url == "http://localhost:3000"
    assert s.langfuse_tracing_enabled is True


def test_langfuse_custom_settings():
    s = make(
        langfuse_public_key="pk-lf-123",
        langfuse_secret_key="sk-lf-456",
        langfuse_base_url="https://us.cloud.langfuse.com",
        langfuse_tracing_enabled=False,
    )
    assert s.langfuse_public_key is not None
    assert s.langfuse_public_key.get_secret_value() == "pk-lf-123"
    assert s.langfuse_secret_key is not None
    assert s.langfuse_secret_key.get_secret_value() == "sk-lf-456"
    assert s.langfuse_base_url == "https://us.cloud.langfuse.com"
    assert s.langfuse_tracing_enabled is False


def test_secrets_hidden_in_repr():
    assert "k'" not in repr(make().llm_api_key)


@pytest.mark.parametrize(
    "field,value",
    [
        ("cache_similarity_threshold", 1.5),
        ("cache_similarity_threshold", -0.1),
        ("llm_timeout_seconds", 0),
        ("vector_dimensions", 0),
        ("llm_max_retries", -1),
    ],
)
def test_invalid_values_rejected(field, value):
    with pytest.raises(ValidationError):
        make(**{field: value})


def test_missing_required_rejected(monkeypatch):
    for key in ("LLM_API_KEY", "NEO4J_URI", "NEO4J_PASSWORD"):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)

