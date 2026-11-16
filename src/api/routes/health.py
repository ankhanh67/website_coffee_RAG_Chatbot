"""Health probe endpoints (liveness & readiness)."""

from typing import Any

from fastapi import APIRouter, Response, status

from src.api.dependencies import get_neo4j_client

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def live() -> dict[str, str]:
    """Liveness probe: verifies process is alive and receiving HTTP requests."""
    return {"status": "ok"}


@router.get("/ready")
async def ready(response: Response) -> dict[str, Any]:
    """Readiness probe: verifies external dependencies (Neo4j Aura database) are reachable."""
    neo4j_ok = False
    details: dict[str, Any] = {}

    try:
        neo4j_client = get_neo4j_client()
        await neo4j_client.verify_connectivity()
        neo4j_ok = True
        details["neo4j"] = "connected"
    except Exception as e:  # noqa: BLE001
        details["neo4j"] = f"unhealthy: {e}"

    if not neo4j_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unhealthy", "components": details}

    return {"status": "ready", "components": details}
