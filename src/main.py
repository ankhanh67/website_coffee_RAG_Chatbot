"""FastAPI application entrypoint. Run: uvicorn src.main:app --reload"""

import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response

from src.api.dependencies import get_embeddings_client, get_model_client, get_neo4j_client
from src.api.routes.chat import router as chat_router
from src.api.routes.ui import router as ui_router
from src.observability.logging import dump_json, job_context, setup_logging

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
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
app.include_router(ui_router)
app.include_router(chat_router)


@app.middleware("http")
async def bind_job_context(request: Request, call_next) -> Response:
    if not request.url.path.startswith("/api/"):
        return await call_next(request)
    with job_context(request.headers.get("X-Job-ID")) as job_id:
        t0 = time.perf_counter()
        logger.info(
            "STAGE HTTP INPUT: %s",
            dump_json({"method": request.method, "path": request.url.path, "job_id": job_id}),
        )
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
        response.headers["X-Job-ID"] = job_id
        logger.info(
            "STAGE HTTP OUTPUT: %s",
            dump_json({"status_code": response.status_code, "elapsed_ms": elapsed_ms, "job_id": job_id}),
        )
        return response


@app.get("/health/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
async def ready() -> dict[str, str]:
    neo4j_client = get_neo4j_client()
    async with neo4j_client.session() as session:
        result = await session.run("RETURN 1 AS ok")
        await result.single()
    return {"status": "ready"}
