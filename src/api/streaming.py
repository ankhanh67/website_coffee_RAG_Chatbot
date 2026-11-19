"""Server-Sent Events (SSE) streaming helpers for the chat endpoint."""

import asyncio
from collections.abc import AsyncIterator, Mapping

from src.observability.logging import dump_json
from src.schema.chat import ChatRequest
from src.services.chat_service import ChatService
from src.services.tts_service import TTSService


def format_sse(payload: Mapping[str, object]) -> str:
    """Format dictionary into standard Server-Sent Event data line."""
    return f"data: {dump_json(payload)}\n\n"


async def stream_chat_response(
    request: ChatRequest,
    chat_service: ChatService,
    chunk_size: int = 12,
) -> AsyncIterator[str]:
    """Execute chat turn and stream incremental tokens followed by final TTS text."""
    yield format_sse({
        "event": "start",
        "session_id": request.session_id,
    })

    # Execute agent pipeline
    response = await chat_service.chat(request)

    yield format_sse({
        "event": "routed",
        "action": response.action.value,
    })

    # Stream reply text in readable chunks
    reply = response.reply
    for i in range(0, len(reply), chunk_size):
        chunk = reply[i : i + chunk_size]
        yield format_sse({
            "event": "token",
            "token": chunk,
        })
        await asyncio.sleep(0.01)

    tts_normalized = TTSService.normalize(reply)

    yield format_sse({
        "event": "done",
        "session_id": response.session_id,
        "action": response.action.value,
        "reply": reply,
        "tts_text": tts_normalized,
    })
