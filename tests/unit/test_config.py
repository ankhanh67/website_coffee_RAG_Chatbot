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

