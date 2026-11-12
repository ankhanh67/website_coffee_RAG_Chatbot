"""Base contract for specialized subagents and stub implementations for Phase 2."""

import logging
from abc import ABC, abstractmethod

from src.observability.logging import dump_json
from src.schema.router import RouterAction

logger = logging.getLogger(__name__)


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
        logger.info(
            "STAGE SubAgent(%s).handle INPUT: %s",
            self.action,
            dump_json({"subagent": type(self).__name__, "action": self.action, "session_id": session_id, "message": message}),
        )
        reply = self._reply_template
        logger.info(
            "STAGE SubAgent(%s).handle OUTPUT: %s",
            self.action,
            dump_json({"subagent": type(self).__name__, "action": self.action, "reply": reply}),
        )
        return reply

