"""FastAPI application entrypoint. Run: uvicorn src.main:app --reload"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.dependencies import get_model_client
from src.api.routes.chat import router as chat_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    if get_model_client.cache_info().currsize:
        await get_model_client().aclose()
        get_model_client.cache_clear()


app = FastAPI(title="Website Coffee MAS-LLM", lifespan=lifespan)
app.include_router(chat_router)


@app.get("/health/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}
