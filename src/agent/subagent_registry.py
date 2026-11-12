"""Registry mapping each routable RouterAction to its specialized subagent."""

from src.exceptions import AgentExecutionError
from src.schema.router import RouterAction
from src.subagents.base import BaseSubAgent, StubSubAgent

DEFAULT_STUB_REPLIES: dict[RouterAction, str] = {
    RouterAction.ORDER: "Hệ thống đã ghi nhận yêu cầu đặt món của bạn.",
    RouterAction.CONSULTANT: "Mình sẵn sàng tư vấn đồ uống phù hợp với khẩu vị của bạn.",
    RouterAction.FAQ: "Mình xin giải đáp thông tin về quán cho bạn.",
}


class SubAgentRegistry:
    def __init__(self) -> None:
        self._agents: dict[RouterAction, BaseSubAgent] = {}

    def register(self, agent: BaseSubAgent) -> None:
        self._agents[agent.action] = agent

    def get(self, action: RouterAction) -> BaseSubAgent:
        try:
            return self._agents[action]
        except KeyError as e:
            raise AgentExecutionError(f"No subagent registered for action '{action}'") from e

    @classmethod
    def with_default_stubs(cls) -> "SubAgentRegistry":
        registry = cls()
        for action, reply in DEFAULT_STUB_REPLIES.items():
            registry.register(StubSubAgent(action=action, reply_template=reply))
        return registry

