"""FastAPI application entrypoint. Run: uvicorn src.main:app --reload"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.dependencies import get_embeddings_client, get_model_client, get_neo4j_client
from src.api.middleware import rate_limit_and_metrics_middleware
from src.api.routes.chat import router as chat_router
from src.api.routes.health import router as health_router
from src.api.routes.metrics import router as metrics_router
from src.api.routes.ui import router as ui_router
from src.observability.logging import setup_logging
from src.observability.tracing import configure_tracing, shutdown_tracing

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_tracing()
    yield
    shutdown_tracing()
    if get_model_client.cache_info().currsize:
        await get_model_client().aclose()
        get_model_client.cache_clear()
    if get_embeddings_client.cache_info().currsize:
        await get_embeddings_client().aclose()
        get_embeddings_client.cache_clear()
    if get_neo4j_client.cache_info().currsize:
        await get_neo4j_client().close()
        get_neo4j_client.cache_clear()


app = FastAPI(title="Website Coffee MAS-LLM", lifespan=lifespan)
app.middleware("http")(rate_limit_and_metrics_middleware)

app.include_router(ui_router)
app.include_router(health_router)
app.include_router(metrics_router)
app.include_router(chat_router)
