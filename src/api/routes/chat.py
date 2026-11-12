"""Chat HTTP endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends

from src.api.dependencies import get_chat_service
from src.schema.chat import ChatRequest, ChatResponse
from src.services.chat_service import ChatService

router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    payload: ChatRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatResponse:
    return await service.chat(payload)
