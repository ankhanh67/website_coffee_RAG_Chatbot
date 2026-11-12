import httpx2 as httpx
import pytest

from src.agent.deep_agent import IGNORE_REPLY, DeepAgent
from src.agent.subagent_registry import DEFAULT_STUB_REPLIES, SubAgentRegistry
from src.api.dependencies import get_chat_service
from src.main import app
from src.schema.router import RouterAction, RouterDecision
from src.services.chat_service import ChatService


class StaticRouter:
    def __init__(self, action: RouterAction):
        self.action = action

    async def route(self, message: str) -> RouterDecision:
        return RouterDecision(action=self.action, confidence=0.95)


@pytest.mark.parametrize(
    "action,expected_reply",
    [
        (RouterAction.ORDER, DEFAULT_STUB_REPLIES[RouterAction.ORDER]),
        (RouterAction.CONSULTANT, DEFAULT_STUB_REPLIES[RouterAction.CONSULTANT]),
        (RouterAction.FAQ, DEFAULT_STUB_REPLIES[RouterAction.FAQ]),
        (RouterAction.IGNORE, IGNORE_REPLY),
    ],
)
async def test_post_chat_routes_and_returns_response(action: RouterAction, expected_reply: str):
    service = ChatService(
        DeepAgent(router=StaticRouter(action), registry=SubAgentRegistry.with_default_stubs())
    )
    app.dependency_overrides[get_chat_service] = lambda: service
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/chat", json={"session_id": "sess-1", "message": "Xin chào"}
            )
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json() == {
        "session_id": "sess-1",
        "action": action.value,
        "reply": expected_reply,
    }


async def test_post_chat_rejects_empty_message():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/v1/chat", json={"session_id": "s1", "message": ""})
    assert resp.status_code == 422


async def test_health_live():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
