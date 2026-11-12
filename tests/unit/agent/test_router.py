import json

import httpx2 as httpx
import pytest

from src.agent.router import Router
from src.exceptions import ModelServiceUnavailableError
from src.infrastructure.model_client import ModelClient
from src.schema.router import RouterAction


def jev_response(choice: str, confidence: float) -> dict:
    return {
        "answers": {
            "route": {
                "type": "choice",
                "choice": choice,
                "confidence": confidence,
                "probabilities": {choice: confidence},
            }
        }
    }


class FakeClient:
    def __init__(self, result):
        self.result = result
        self.calls = []

    async def decide(self, model, state, questions):
        self.calls.append((model, state, questions))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def make_router(result, threshold=0.5):
    client = FakeClient(result)
    return Router(client, model="jev", confidence_threshold=threshold), client


async def test_routes_to_jev_choice():
    router, client = make_router(jev_response("order", 0.9))
    decision = await router.route("Cho mình 2 ly bạc xỉu")
    assert decision.action is RouterAction.ORDER
    assert decision.confidence == 0.9
    assert not decision.is_fallback
    model, state, questions = client.calls[0]
    assert model == "jev"
    assert state == {"message": "Cho mình 2 ly bạc xỉu"}
    assert set(questions["route"]["criteria"]) == {a.value for a in RouterAction}


async def test_low_confidence_falls_back_to_ignore():
    router, _ = make_router(jev_response("faq", 0.3), threshold=0.5)
    decision = await router.route("hmm")
    assert decision.action is RouterAction.IGNORE
    assert decision.is_fallback
    assert decision.confidence == 0.3


async def test_service_error_falls_back_to_ignore():
    router, _ = make_router(ModelServiceUnavailableError("down"))
    decision = await router.route("hi")
    assert decision.action is RouterAction.IGNORE
    assert decision.is_fallback


@pytest.mark.parametrize(
    "bad",
    [{}, {"answers": {}}, jev_response("dance", 0.9), jev_response("order", 7.0)],
)
async def test_malformed_output_falls_back_to_ignore(bad):
    router, _ = make_router(bad)
    decision = await router.route("hi")
    assert decision.action is RouterAction.IGNORE
    assert decision.is_fallback


def make_client(handler, max_retries=2):
    return ModelClient(
        api_key="k",
        decisions_url="https://example.test/decisions",
        timeout_seconds=1,
        max_retries=max_retries,
        transport=httpx.MockTransport(handler),
        retry_backoff_seconds=0,
    )


async def test_model_client_retries_then_succeeds():
    calls = []

    def handler(request):
        calls.append(json.loads(request.content))
        if len(calls) < 3:
            return httpx.Response(503)
        return httpx.Response(200, json=jev_response("faq", 0.8))

    client = make_client(handler)
    result = await client.decide("jev", {"message": "x"}, {"q": {}})
    assert result["answers"]["route"]["choice"] == "faq"
    assert len(calls) == 3
    assert calls[0] == {"model": "jev", "state": {"message": "x"}, "questions": {"q": {}}}


async def test_model_client_raises_after_retries_exhausted():
    calls = []

    def handler(request):
        calls.append(1)
        raise httpx.ConnectTimeout("timeout")

    client = make_client(handler, max_retries=1)
    with pytest.raises(ModelServiceUnavailableError):
        await client.decide("jev", {}, {})
    assert len(calls) == 2


async def test_model_client_does_not_retry_client_errors():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(401, json={"error": "bad key"})

    client = make_client(handler)
    with pytest.raises(ModelServiceUnavailableError):
        await client.decide("jev", {}, {})
    assert len(calls) == 1

