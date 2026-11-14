"""Chat HTTP endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from src.api.dependencies import get_chat_service
from src.api.streaming import stream_chat_response
from src.schema.chat import ChatRequest, ChatResponse
from src.services.chat_service import ChatService

router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    payload: ChatRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatResponse:
    return await service.chat(payload)


@router.post("/chat/stream")
async def chat_stream_endpoint(
    payload: ChatRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> StreamingResponse:
    """Stream chat response tokens and TTS-ready text via Server-Sent Events (SSE)."""
    generator = stream_chat_response(payload, service)
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
