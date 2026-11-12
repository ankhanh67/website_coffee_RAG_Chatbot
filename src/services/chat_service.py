"""Application service for handling customer chat messages."""

from src.agent.deep_agent import DeepAgent
from src.schema.chat import ChatRequest, ChatResponse


class ChatService:
    def __init__(self, deep_agent: DeepAgent) -> None:
        self._deep_agent = deep_agent

    async def chat(self, request: ChatRequest) -> ChatResponse:
        return await self._deep_agent.handle(request)
