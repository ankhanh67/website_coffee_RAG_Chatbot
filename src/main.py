"""FastAPI application entrypoint. Run: uvicorn src.main:app --reload"""

from fastapi import FastAPI

app = FastAPI(title="Website Coffee MAS-LLM")


@app.get("/health/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}

