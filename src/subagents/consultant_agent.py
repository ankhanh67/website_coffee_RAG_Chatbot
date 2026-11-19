"""ConsultantAgent built with `ToolEnabledSubAgent` and `@tool`."""

from collections.abc import Sequence

from langchain.tools import tool
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.checkpoint.memory import InMemorySaver

from src.agent.llm import ChatModelProvider
from src.prompt.consultant_agent import CONSULTANT_AGENT_SYSTEM_PROMPT
from src.rag.retrieval.base import BaseRetriever
from src.schema.router import RouterAction
from src.subagents.base import ToolEnabledSubAgent


def build_consultant_tools(retriever: BaseRetriever, top_k: int = 8) -> list[BaseTool]:
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


class ConsultantAgent(ToolEnabledSubAgent):
    action = RouterAction.CONSULTANT
    system_prompt = CONSULTANT_AGENT_SYSTEM_PROMPT
    default_temperature = 0.2

    def __init__(
        self,
        model_client: ChatModelProvider | BaseChatModel,
        retriever: BaseRetriever,
        model: str = "google/gemini-2.5-flash",
        top_k: int = 8,
        checkpointer: InMemorySaver | None = None,
    ) -> None:
        super().__init__(model_client=model_client, model=model, checkpointer=checkpointer)
        self._retriever = retriever
        self._top_k = top_k

    def _build_tools(self, session_id: str) -> Sequence[BaseTool]:
        del session_id
        return build_consultant_tools(self._retriever, top_k=self._top_k)
