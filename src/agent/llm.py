"""LangChain ChatOpenAI and LCEL chain builders for OpenRouter LLM interactions."""

import re
from typing import Any, TypeVar

import httpx2 as httpx
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, SecretStr

T = TypeVar("T", bound=BaseModel)

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def strip_json_fences(raw: str) -> str:
    """Strip markdown ```json ... ``` fences if present around JSON output."""
    text = raw.strip()
    if text.startswith("```"):
        text = _CODE_FENCE_RE.sub("", text).strip()
    return text


def build_chat_prompt() -> ChatPromptTemplate:
    """Create standard system + human ChatPromptTemplate."""
    return ChatPromptTemplate.from_messages(
        [
            ("system", "{system_prompt}"),
            ("human", "{user_message}"),
        ]
    )


def build_chat_model(
    model: str,
    api_key: str,
    base_url: str = "https://openrouter.ai/api/v1",
    temperature: float = 0.0,
    timeout_seconds: float = 30.0,
    max_retries: int = 2,
    http_async_client: httpx.AsyncClient | None = None,
    model_kwargs: dict[str, Any] | None = None,
) -> ChatOpenAI:
    """Instantiate a LangChain ChatOpenAI model pointing to OpenRouter."""
    return ChatOpenAI(
        model=model,
        api_key=SecretStr(api_key),
        base_url=base_url,
        temperature=temperature,
        timeout=timeout_seconds,
        max_retries=max_retries,
        http_async_client=http_async_client,
        model_kwargs=model_kwargs or {},
    )


def build_text_chain(chat_model: ChatOpenAI) -> Runnable[dict[str, Any], str]:
    """Build an LCEL chain: ChatPromptTemplate | ChatOpenAI | StrOutputParser."""
    prompt = build_chat_prompt()
    return prompt | chat_model | StrOutputParser() | RunnableLambda(lambda s: s.strip())


def build_structured_chain(
    chat_model: ChatOpenAI,
    response_model: type[T],
) -> Runnable[dict[str, Any], T]:
    """Build an LCEL chain that parses and validates LLM JSON output into a Pydantic model."""
    prompt = build_chat_prompt()

    def _parse_pydantic(raw: str) -> T:
        cleaned = strip_json_fences(raw)
        return response_model.model_validate_json(cleaned)

    return prompt | chat_model | StrOutputParser() | RunnableLambda(_parse_pydantic)
