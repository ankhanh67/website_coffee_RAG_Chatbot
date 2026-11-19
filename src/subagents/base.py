"""Base contracts for specialized subagents, shared LangChain tool execution, and test stubs."""

import logging
from abc import ABC, abstractmethod
from collections.abc import Sequence

from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langgraph.checkpoint.memory import InMemorySaver

from src.agent.llm import ChatModelProvider, resolve_chat_model
from src.observability.logging import dump_json
from src.observability.tracing import get_langchain_callbacks, trace_observation
from src.schema.router import RouterAction

logger = logging.getLogger(__name__)


class BaseSubAgent(ABC):
    action: RouterAction

    @abstractmethod
    async def handle(self, message: str, session_id: str) -> str:
        """Process a user message and return the assistant reply text."""


class ToolEnabledSubAgent(BaseSubAgent):
    """Shared base class for subagents powered by `langchain.agents.create_agent` and `@tool`."""

    system_prompt: str
    default_temperature: float = 0.2

    def __init__(
        self,
        model_client: ChatModelProvider | BaseChatModel,
        model: str = "google/gemini-2.5-flash",
        checkpointer: InMemorySaver | None = None,
    ) -> None:
        self._model_client = model_client
        self._model = model
        self._checkpointer = checkpointer or InMemorySaver()

    def _resolve_chat_model(self) -> BaseChatModel:
        return resolve_chat_model(
            self._model_client,
            model=self._model,
            temperature=self.default_temperature,
        )

    @abstractmethod
    def _build_tools(self, session_id: str) -> Sequence[BaseTool]:
        """Return the domain tools bound for the current turn."""

    async def handle(self, message: str, session_id: str) -> str:
        stage_name = f"{type(self).__name__}.handle"
        input_payload = {"session_id": session_id, "message": message, "model": self._model}
        logger.info("STAGE %s INPUT: %s", stage_name, dump_json(input_payload))
        with trace_observation(stage_name, as_type="agent", input=input_payload) as span:
            chat_model = self._resolve_chat_model()
            tools = list(self._build_tools(session_id))
            agent = create_agent(
                model=chat_model,
                tools=tools,
                system_prompt=self.system_prompt,
                checkpointer=self._checkpointer,
            )

            invoke_config: RunnableConfig = {
                "configurable": {"thread_id": f"{self.action.value}:{session_id}"}
            }
            callbacks = get_langchain_callbacks()
            if callbacks:
                invoke_config["callbacks"] = callbacks

            result = await agent.ainvoke(
                {"messages": [{"role": "user", "content": message}]},
                config=invoke_config,
            )
            messages = result.get("messages", [])
            reply = str(messages[-1].content).strip() if messages else ""

            span.update(output={"reply": reply})
            logger.info(
                "STAGE %s OUTPUT: %s",
                stage_name,
                dump_json({"session_id": session_id, "reply": reply}),
            )
            return reply


class StubSubAgent(BaseSubAgent):
    """Minimal placeholder subagent used before full RAG/domain logic is wired."""

    def __init__(self, action: RouterAction, reply_template: str) -> None:
        self.action = action
        self._reply_template = reply_template

    async def handle(self, message: str, session_id: str) -> str:
        logger.info(
            "STAGE SubAgent(%s).handle INPUT: %s",
            self.action,
            dump_json(
                {
                    "subagent": type(self).__name__,
                    "action": self.action,
                    "session_id": session_id,
                    "message": message,
                }
            ),
        )
        reply = self._reply_template
        logger.info(
            "STAGE SubAgent(%s).handle OUTPUT: %s",
            self.action,
            dump_json({"subagent": type(self).__name__, "action": self.action, "reply": reply}),
        )
        return reply

