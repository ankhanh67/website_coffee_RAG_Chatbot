"""Unit tests for ConsultantAgent and FAQAgent built with `create_agent` and `@tool`."""

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from src.rag.retrieval.base import BaseRetriever
from src.schema.retrieval import HybridRetrievalResult, RetrievedItem
from src.schema.router import RouterAction
from src.subagents.consultant_agent import ConsultantAgent
from src.subagents.faq_agent import FAQAgent


class FakeToolCallingChatModel(GenericFakeChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


class FakeRetriever(BaseRetriever):
    def __init__(self, result: HybridRetrievalResult) -> None:
        self._result = result
        self.queries: list[str] = []

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        include_menu: bool = True,
        include_chunks: bool = True,
        expand_graph: bool = True,
    ) -> HybridRetrievalResult:
        self.queries.append(query)
        return self._result


async def test_consultant_agent_calls_search_menu_tool_and_returns_grounded_reply():
    fake_result = HybridRetrievalResult(
        query="đồ uống không caffeine thuần chay",
        items=[
            RetrievedItem(
                node_id="M045",
                source_type="menu",
                title="Trà Atiso (Artichoke Tea)",
                text="[M045] Trà Atiso - Giá: Size S: 39.000đ, Size M: 45.000đ, Size L: 55.000đ. Caffeine: không. Thuần chay: có.",
                score=0.92,
                hop_type="vector",
            ),
            RetrievedItem(
                node_id="M064",
                source_type="menu",
                title="Nước Ép Cam (Fresh Orange Juice)",
                text="[M064] Nước Ép Cam - Giá: Size M: 49.000đ. Caffeine: không. Thuần chay: có.",
                score=0.89,
                hop_type="vector",
            ),
        ],
        has_sufficient_evidence=True,
    )
    retriever = FakeRetriever(fake_result)

    llm = FakeToolCallingChatModel(
        messages=iter([
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "search_menu_and_recommendations",
                        "args": {"query": "đồ uống không caffeine thuần chay"},
                        "id": "call_consultant_1",
                    }
                ],
            ),
            AIMessage(
                content=(
                    "Bạn có thể thử Trà Atiso (Size S: 39.000đ, Size M: 45.000đ, Size L: 55.000đ) "
                    "hoặc Nước Ép Cam (Size M: 49.000đ), cả hai đều không có caffeine và thuần chay ạ!"
                )
            ),
        ])
    )

    agent = ConsultantAgent(model_client=llm, retriever=retriever)
    assert agent.action is RouterAction.CONSULTANT

    reply = await agent.handle(
        message="Quán có đồ uống nào không có caffeine và thuần chay?",
        session_id="sess-consult-1",
    )
    assert retriever.queries == ["đồ uống không caffeine thuần chay"]
    assert "Trà Atiso" in reply
    assert "39.000đ" in reply
    assert "Nước Ép Cam" in reply


async def test_consultant_agent_handles_out_of_scope_menu_item():
    fake_result = HybridRetrievalResult(
        query="phở bò",
        items=[],
        has_sufficient_evidence=False,
    )
    retriever = FakeRetriever(fake_result)

    llm = FakeToolCallingChatModel(
        messages=iter([
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "search_menu_and_recommendations",
                        "args": {"query": "phở bò"},
                        "id": "call_consultant_2",
                    }
                ],
            ),
            AIMessage(
                content=(
                    "Menu của quán hiện không có phở bò ạ. Quán chỉ phục vụ đồ uống, bánh ngọt "
                    "và một số món mặn như bánh mì, mì Ý, salad, cơm gà."
                )
            ),
        ])
    )

    agent = ConsultantAgent(model_client=llm, retriever=retriever)
    reply = await agent.handle(
        message="Quán có bán phở bò không?",
        session_id="sess-consult-2",
    )
    assert retriever.queries == ["phở bò"]
    assert "không có phở bò" in reply.lower()


async def test_faq_agent_calls_search_store_knowledge_tool_and_synthesizes_multi_chunk():
    fake_result = HybridRetrievalResult(
        query="Hạng Vàng cần bao nhiêu điểm và đổi được gì",
        items=[
            RetrievedItem(
                node_id="doc-policy-08",
                source_type="document",
                title="Chương trình thành viên HL Rewards",
                text="Thành viên có từ 500 điểm tích lũy trong năm được nâng lên hạng Vàng.",
                score=0.91,
                hop_type="vector",
            ),
            RetrievedItem(
                node_id="doc-policy-09",
                source_type="document",
                title="Quy định đổi điểm thưởng",
                text="100 điểm được đổi lấy 1 đồ uống size M bất kỳ trong menu, không bao gồm topping.",
                score=0.84,
                hop_type="next",
            ),
        ],
        has_sufficient_evidence=True,
    )
    retriever = FakeRetriever(fake_result)

    llm = FakeToolCallingChatModel(
        messages=iter([
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "search_store_knowledge",
                        "args": {"query": "Hạng Vàng cần bao nhiêu điểm và đổi được gì"},
                        "id": "call_faq_1",
                    }
                ],
            ),
            AIMessage(
                content=(
                    "Hạng Vàng cần từ 500 điểm tích lũy trong năm. Với mỗi 100 điểm thưởng, "
                    "bạn đổi được 1 đồ uống size M bất kỳ trong menu (không gồm topping)."
                )
            ),
        ])
    )

    agent = FAQAgent(model_client=llm, retriever=retriever)
    assert agent.action is RouterAction.FAQ

    reply = await agent.handle(
        message="Hạng Vàng cần bao nhiêu điểm và điểm thưởng đổi được gì?",
        session_id="sess-faq-1",
    )
    assert retriever.queries == ["Hạng Vàng cần bao nhiêu điểm và đổi được gì"]
    assert "500 điểm" in reply
    assert "100 điểm" in reply
