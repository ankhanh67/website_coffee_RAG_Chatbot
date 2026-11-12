"""Base contract for specialized subagents and stub implementations for Phase 2."""

from abc import ABC, abstractmethod

from src.schema.router import RouterAction


class BaseSubAgent(ABC):
    action: RouterAction

    @abstractmethod
    async def handle(self, message: str, session_id: str) -> str:
        """Process a user message and return the assistant reply text."""


class StubSubAgent(BaseSubAgent):
    """Minimal placeholder subagent used before full RAG/domain logic is wired."""

    def __init__(self, action: RouterAction, reply_template: str):
        self.action = action
        self._reply_template = reply_template

    async def handle(self, message: str, session_id: str) -> str:
        return self._reply_template
