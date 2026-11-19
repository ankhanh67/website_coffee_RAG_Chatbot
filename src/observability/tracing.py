"""Langfuse distributed tracing and LangChain callback integration."""

import logging
import os
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from types import MappingProxyType
from typing import Protocol

from langchain_core.callbacks import BaseCallbackHandler
from langfuse import Langfuse, ObservationTypeLiteral, propagate_attributes
from langfuse._client.resource_manager import LangfuseResourceManager
from langfuse.langchain import CallbackHandler
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SpanExporter
from pydantic import ValidationError

from src.config import Settings, get_settings

logger = logging.getLogger(__name__)

_langfuse_client: Langfuse | None = None
_initialized: bool = False


class ObservationHandle(Protocol):
    """Protocol for an active Langfuse observation or a safe no-op fallback."""

    def update(self, **kwargs: object) -> object: ...
    def score(self, **kwargs: object) -> object: ...


class _NoOpObservation:
    """No-op observation object returned when Langfuse tracing is disabled."""

    def update(self, **_: object) -> "_NoOpObservation":
        return self

    def score(self, **_: object) -> "_NoOpObservation":
        return self


_NOOP_OBSERVATION = _NoOpObservation()
_EMPTY_METADATA: Mapping[str, object] = MappingProxyType({})


def configure_tracing(
    settings: Settings | None = None,
    *,
    span_exporter: SpanExporter | None = None,
) -> Langfuse | None:
    """Initialize (or reconfigure) the singleton Langfuse client from application settings."""
    global _langfuse_client, _initialized
    s = settings or get_settings()

    pub = s.langfuse_public_key.get_secret_value().strip() if s.langfuse_public_key else ""
    sec = s.langfuse_secret_key.get_secret_value().strip() if s.langfuse_secret_key else ""

    if not s.langfuse_tracing_enabled or not pub or not sec:
        _langfuse_client = None
        _initialized = True
        return None

    tracer_provider = TracerProvider() if span_exporter is not None else None
    _langfuse_client = Langfuse(
        public_key=pub,
        secret_key=sec,
        base_url=s.langfuse_base_url,
        tracing_enabled=True,
        span_exporter=span_exporter,
        tracer_provider=tracer_provider,
    )
    _initialized = True
    logger.info("Langfuse tracing enabled (base_url=%s)", s.langfuse_base_url)
    return _langfuse_client


def get_langfuse_client() -> Langfuse | None:
    """Return the active Langfuse client, lazily initializing from Settings on first call outside pytest."""
    global _initialized
    if not _initialized:
        if "PYTEST_CURRENT_TEST" in os.environ:
            return None
        try:
            configure_tracing(get_settings())
        except (ValidationError, ValueError, RuntimeError, OSError) as e:
            logger.debug("Skipping lazy Langfuse initialization: %s", e)
            _initialized = True
    return _langfuse_client


def is_tracing_enabled() -> bool:
    """Return True when a configured Langfuse client is active."""
    return get_langfuse_client() is not None


def shutdown_tracing() -> None:
    """Flush pending observations and shut down the Langfuse client cleanly."""
    global _langfuse_client, _initialized
    if _langfuse_client is not None:
        try:
            _langfuse_client.flush()
            _langfuse_client.shutdown()
        except (RuntimeError, ValueError, OSError) as e:
            logger.warning("Error flushing Langfuse client on shutdown: %s", e)
    LangfuseResourceManager.reset()
    _langfuse_client = None
    _initialized = False


def get_langchain_callbacks() -> list[BaseCallbackHandler]:
    """Return a list containing a Langfuse `CallbackHandler` if tracing is enabled, else `[]`."""
    client = get_langfuse_client()
    if client is None or client._resources is None:
        return []
    return [CallbackHandler(public_key=client._resources.public_key)]


@contextmanager
def trace_chat_request(
    session_id: str,
    message: str,
    job_id: str = "",
) -> Iterator[ObservationHandle]:
    """Start the root Langfuse trace span for a customer chat turn with propagated session & job metadata."""
    client = get_langfuse_client()
    if client is None:
        yield _NOOP_OBSERVATION
        return

    meta: dict[str, str] = {"job_id": job_id} if job_id else {}
    with (
        client.start_as_current_observation(
            as_type="span",
            name="chat_request",
            input={"session_id": session_id, "message": message},
            metadata=meta,
        ) as root_span,
        propagate_attributes(
            session_id=session_id,
            trace_name="chat_request",
            metadata=meta,
            tags=["website_coffee"],
        ),
    ):
        yield root_span


@contextmanager
def trace_observation(
    name: str,
    *,
    as_type: ObservationTypeLiteral = "span",
    input: object = "",
    model: str = "",
    metadata: Mapping[str, object] = _EMPTY_METADATA,
) -> Iterator[ObservationHandle]:
    """Create a nested Langfuse observation (span, generation, retriever, embedding, etc.)."""
    client = get_langfuse_client()
    if client is None:
        yield _NOOP_OBSERVATION
        return

    kwargs: dict[str, object] = {
        "name": name,
        "as_type": as_type,
        "input": input,
    }
    if metadata:
        kwargs["metadata"] = dict(metadata)
    if model and as_type in ("generation", "embedding"):
        kwargs["model"] = model

    with client.start_as_current_observation(**kwargs) as obs:
        yield obs
