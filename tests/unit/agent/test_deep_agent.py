import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from src.agent.deep_agent import IGNORE_REPLY, DeepAgent
from src.agent.subagent_registry import DEFAULT_STUB_REPLIES, SubAgentRegistry
from src.exceptions import AgentExecutionError
from src.schema.chat import ChatRequest
from src.schema.order import MenuMatch
from src.schema.router import RouterAction, RouterDecision


class FakeRouter:
    def __init__(self, action: RouterAction, confidence: float = 0.95):
        self.decision = RouterDecision(action=action, confidence=confidence)
        self.seen_messages: list[str] = []

    async def route(self, message: str) -> RouterDecision:
        self.seen_messages.append(message)
        return self.decision


@pytest.mark.parametrize(
    "action",
    [RouterAction.ORDER, RouterAction.CONSULTANT, RouterAction.FAQ],
)
async def test_deep_agent_dispatches_to_registered_subagent(action: RouterAction):
    router = FakeRouter(action)
    agent = DeepAgent(router=router, registry=SubAgentRegistry.with_default_stubs())
    resp = await agent.handle(ChatRequest(session_id="s1", message="Cho mình 1 bạc xỉu"))

    assert resp.session_id == "s1"
    assert resp.action is action
    assert resp.reply == DEFAULT_STUB_REPLIES[action]
    assert router.seen_messages == ["Cho mình 1 bạc xỉu"]


async def test_deep_agent_returns_ignore_reply_without_calling_registry():
    router = FakeRouter(RouterAction.IGNORE)
    empty_registry = SubAgentRegistry()
    agent = DeepAgent(router=router, registry=empty_registry)
    resp = await agent.handle(ChatRequest(session_id="s2", message="ờ ờ"))

    assert resp.action is RouterAction.IGNORE
    assert resp.reply == IGNORE_REPLY


def test_registry_raises_when_action_missing():
    registry = SubAgentRegistry()
    with pytest.raises(AgentExecutionError):
        registry.get(RouterAction.ORDER)


def test_menu_match_line_total_uses_exact_int_math():
    item = MenuMatch(item_id="M001", name_vi="Phin Sữa Đá", size="M", unit_price_vnd=39000, quantity=3)
    assert item.line_total_vnd == 117000
    assert isinstance(item.line_total_vnd, int)


class FakeSupervisorLLM(GenericFakeChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


async def test_deep_agent_supervisor_calls_multiple_subagent_tools():
    router = FakeRouter(RouterAction.FAQ)
    supervisor_llm = FakeSupervisorLLM(
        messages=iter([
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "call_faq_agent", "args": {"query": "Mấy giờ đóng cửa?"}, "id": "c1"},
                    {"name": "call_order_agent", "args": {"query": "Đặt 1 Bạc Xỉu"}, "id": "c2"},
                ],
            ),
            AIMessage(
                content="Quán mở cửa đến 22h và mình đã ghi nhận đơn 1 Bạc Xỉu của bạn ạ!"
            ),
        ])
    )
    agent = DeepAgent(
        router=router,
        registry=SubAgentRegistry.with_default_stubs(),
        model_client=supervisor_llm,
    )
    resp = await agent.handle(
        ChatRequest(session_id="s-multi", message="Quán mấy giờ đóng cửa và cho mình đặt 1 Bạc Xỉu")
    )
    assert resp.action is RouterAction.ORDER
    assert "22h" in resp.reply
    assert "Bạc Xỉu" in resp.reply



