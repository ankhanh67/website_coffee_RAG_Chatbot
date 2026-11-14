"""Unit tests for Order schemas and ModelClient.generate_structured / generate_text."""

import json

import httpx2 as httpx
import pytest

from src.exceptions import ModelServiceUnavailableError
from src.infrastructure.model_client import ModelClient
from src.schema.order import (
    MenuMatch,
    OrderCalculation,
    OrderExtraction,
    OrderIntentType,
    OrderItemInput,
    OrderStatus,
)


def make_client(handler, max_retries: int = 2) -> ModelClient:
    return ModelClient(
        api_key="test-key",
        decisions_url="https://example.test/decisions",
        base_url="https://example.test/v1",
        timeout_seconds=1.0,
        max_retries=max_retries,
        transport=httpx.MockTransport(handler),
        retry_backoff_seconds=0.0,
    )


def test_order_schemas_validation():
    item = OrderItemInput(name="Bạc xỉu", size="L", quantity=2, note="ít đá", action=OrderIntentType.ADD)
    extraction = OrderExtraction(intent=OrderIntentType.ADD, items=[item])
    assert extraction.intent is OrderIntentType.ADD
    assert extraction.items[0].action is OrderIntentType.ADD

    match = MenuMatch(
        item_id="M077",
        name_vi="Bánh Tiramisu",
        requested_name="tiramisu",
        size="Một cỡ",
        unit_price_vnd=45000,
        quantity=2,
        note="",
    )
    assert match.line_total_vnd == 90000

    calc = OrderCalculation(
        status=OrderStatus.PENDING_CONFIRMATION,
        items=[match],
        subtotal_vnd=90000,
        total_vnd=90000,
    )
    assert calc.status is OrderStatus.PENDING_CONFIRMATION
    assert calc.total_vnd == 90000


async def test_generate_structured_parses_clean_and_fenced_json():
    responses = [
        '{"intent": "add", "items": [{"name": "Phin Sữa Đá", "size": "L", "quantity": 2}]}',
        '```json\n{"intent": "confirm", "items": []}\n```',
    ]
    call_idx = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_idx
        assert str(request.url) == "https://example.test/v1/chat/completions"
        content = responses[call_idx]
        call_idx += 1
        return httpx.Response(
            200,
            json={"choices": [{"message": {"role": "assistant", "content": content}}]},
        )

    client = make_client(handler)
    res1 = await client.generate_structured(
        model="google/gemini-2.5-flash",
        system_prompt="Extract order",
        user_message="Cho 2 phin sữa đá size L",
        response_model=OrderExtraction,
    )
    assert res1.intent is OrderIntentType.ADD
    assert len(res1.items) == 1
    assert res1.items[0].name == "Phin Sữa Đá"
    assert res1.items[0].size == "L"
    assert res1.items[0].quantity == 2

    res2 = await client.generate_structured(
        model="google/gemini-2.5-flash",
        system_prompt="Extract order",
        user_message="Xác nhận đơn",
        response_model=OrderExtraction,
    )
    assert res2.intent is OrderIntentType.CONFIRM
    assert res2.items == []
    await client.aclose()


async def test_generate_text_retries_and_returns_text():
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        body = json.loads(request.content)
        assert body["model"] == "google/gemini-2.5-flash"
        if attempts == 1:
            return httpx.Response(503, text="Service Unavailable")
        return httpx.Response(
            200,
            json={"choices": [{"message": {"role": "assistant", "content": "Xin chào quý khách!"}}]},
        )

    client = make_client(handler, max_retries=2)
    reply = await client.generate_text(
        model="google/gemini-2.5-flash",
        system_prompt="Be polite",
        user_message="Hi",
    )
    assert reply == "Xin chào quý khách!"
    assert attempts == 2
    await client.aclose()


async def test_generate_structured_raises_on_invalid_json():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"role": "assistant", "content": "not valid json"}}]},
        )

    client = make_client(handler, max_retries=0)
    with pytest.raises(ModelServiceUnavailableError):
        await client.generate_structured(
            model="google/gemini-2.5-flash",
            system_prompt="Extract",
            user_message="Hi",
            response_model=OrderExtraction,
        )
    await client.aclose()

