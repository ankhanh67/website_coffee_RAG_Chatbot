"""Health probe endpoints (liveness & readiness)."""

from typing import Literal

from fastapi import APIRouter, Response, status
from neo4j.exceptions import Neo4jError
from pydantic import BaseModel

from src.api.dependencies import get_neo4j_client

router = APIRouter(prefix="/health", tags=["health"])


class LivenessResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ReadinessResponse(BaseModel):
    status: Literal["ready", "unhealthy"]
    components: dict[str, str]


@router.get("/live", response_model=LivenessResponse)
async def live() -> LivenessResponse:
    """Liveness probe: verifies process is alive and receiving HTTP requests."""
    return LivenessResponse()


@router.get("/ready", response_model=ReadinessResponse)
async def ready(response: Response) -> ReadinessResponse:
    """Readiness probe: verifies external dependencies (Neo4j Aura database) are reachable."""
    neo4j_ok = False
    details: dict[str, str] = {}

    try:
        neo4j_client = get_neo4j_client()
        await neo4j_client.verify_connectivity()
        neo4j_ok = True
        details["neo4j"] = "connected"
    except (Neo4jError, OSError, RuntimeError, ValueError) as e:
        details["neo4j"] = f"unhealthy: {e}"

    if not neo4j_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadinessResponse(status="unhealthy", components=details)

    return ReadinessResponse(status="ready", components=details)
