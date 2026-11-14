"""ConsultantAgent built with `langchain.agents.create_agent` and `@tool`."""

import logging
from typing import Any, Protocol

from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.language_models.chat_models import BaseChatModel

from src.observability.logging import dump_json
from src.prompt.consultant_agent import CONSULTANT_AGENT_SYSTEM_PROMPT
from src.rag.retrieval.base import BaseRetriever
from src.schema.router import RouterAction
from src.subagents.base import BaseSubAgent

logger = logging.getLogger(__name__)


class ChatModelProvider(Protocol):
    def get_chat_model(
        self,
        model: str,
        temperature: float = 0.0,
        model_kwargs: dict[str, Any] | None = None,
    ) -> BaseChatModel: ...


def build_consultant_tools(retriever: BaseRetriever, top_k: int = 8) -> list[Any]:
    """Create LangChain `@tool` functions bound to `retriever` for menu consultation."""

    @tool
    async def search_menu_and_recommendations(query: str) -> str:
        """Tìm kiếm thông tin món uống, bánh ngọt, món mặn, giá bán theo size, caffeine, thuần chay (vegan) và dị ứng (allergens) trong menu và FAQ."""
        result = await retriever.retrieve(
            query=query,
            top_k=top_k,
            include_menu=True,
            include_chunks=True,
            expand_graph=True,
        )
        return result.model_dump_json()

    return [search_menu_and_recommendations]


class ConsultantAgent(BaseSubAgent):
    action = RouterAction.CONSULTANT

    def __init__(
        self,
        model_client: ChatModelProvider | BaseChatModel,
        retriever: BaseRetriever,
        model: str = "google/gemini-2.5-flash",
        top_k: int = 8,
    ) -> None:
        self._model_client = model_client
        self._retriever = retriever
        self._model = model
        self._top_k = top_k

    def _resolve_chat_model(self) -> BaseChatModel:
        if isinstance(self._model_client, BaseChatModel):
            return self._model_client
        return self._model_client.get_chat_model(model=self._model, temperature=0.2)

    async def handle(self, message: str, session_id: str) -> str:
        logger.info(
            "STAGE ConsultantAgent.handle INPUT: %s",
            dump_json({"session_id": session_id, "message": message, "model": self._model}),
        )
        chat_model = self._resolve_chat_model()
        tools = build_consultant_tools(self._retriever, top_k=self._top_k)
        agent = create_agent(
            model=chat_model,
            tools=tools,
            system_prompt=CONSULTANT_AGENT_SYSTEM_PROMPT,
        )

        result = await agent.ainvoke({"messages": [{"role": "user", "content": message}]})
        messages = result.get("messages", [])
        reply = str(messages[-1].content).strip() if messages else ""

        logger.info(
            "STAGE ConsultantAgent.handle OUTPUT: %s",
            dump_json({"session_id": session_id, "reply": reply}),
        )
        return reply
