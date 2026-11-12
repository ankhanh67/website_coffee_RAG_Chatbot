from unittest.mock import AsyncMock, MagicMock

import pytest

from src.exceptions import RetrievalError
from src.rag.graph.client import Neo4jClient
from src.rag.graph.repository import Neo4jRepository
from src.schema.retrieval import MenuItemRecord


@pytest.fixture
def mock_driver():
    driver = MagicMock()
    driver.verify_connectivity = AsyncMock()
    driver.close = AsyncMock()
    return driver


@pytest.fixture
def mock_session():
    session = MagicMock()
    session.run = AsyncMock()
    session.close = AsyncMock()
    return session


async def test_init_schema_executes_queries(mock_driver, mock_session):
    mock_driver.session = MagicMock(return_value=mock_session)
    mock_session.__aenter__.return_value = mock_session

    client = Neo4jClient(uri="neo4j+s://x", username="u", password="p")
    client._driver = mock_driver

    repo = Neo4jRepository(client)
    await repo.init_schema(vector_dimensions=768)

    assert mock_session.run.await_count >= 3


async def test_upsert_menu_item(mock_driver, mock_session):
    mock_driver.session = MagicMock(return_value=mock_session)
    mock_session.__aenter__.return_value = mock_session

    client = Neo4jClient(uri="neo4j+s://x", username="u", password="p")
    client._driver = mock_driver

    repo = Neo4jRepository(client)
    item = MenuItemRecord(
        item_id="M001",
        name_vi="Phin Sữa Đá",
        name_en="Iced Vietnamese Milk Coffee",
        category="Cà phê",
        category_en="Coffee",
        price_m=39000,
        sizes=["M"],
        temperature="iced",
        caffeine="có",
        vegan="không",
    )
    dummy_embedding = [0.1] * 768
    await repo.upsert_menu_item(item, dummy_embedding)

    assert mock_session.run.await_count == 1
    call_args = mock_session.run.await_args[1]
    assert call_args["item_id"] == "M001"
    assert call_args["embedding"] == dummy_embedding


async def test_get_menu_item_found(mock_driver, mock_session):
    mock_driver.session = MagicMock(return_value=mock_session)
    mock_session.__aenter__.return_value = mock_session

    mock_result = MagicMock()
    mock_result.single = AsyncMock(
        return_value={
            "item": {
                "item_id": "M001",
                "name_vi": "Phin Sữa Đá",
                "name_en": "Coffee",
                "category": "Cà phê",
                "category_en": "Coffee",
                "price_m": 39000,
                "sizes": ["M"],
                "temperature": "iced",
                "caffeine": "có",
                "vegan": "không",
                "allergens": [],
                "ingredients": "",
                "description_vi": "",
                "description_en": "",
            }
        }
    )
    mock_session.run.return_value = mock_result

    client = Neo4jClient(uri="neo4j+s://x", username="u", password="p")
    client._driver = mock_driver

    repo = Neo4jRepository(client)
    res = await repo.get_menu_item("M001")
    assert res is not None
    assert res.item_id == "M001"
    assert res.price_m == 39000


async def test_get_menu_item_not_found(mock_driver, mock_session):
    mock_driver.session = MagicMock(return_value=mock_session)
    mock_session.__aenter__.return_value = mock_session

    mock_result = MagicMock()
    mock_result.single = AsyncMock(return_value=None)
    mock_session.run.return_value = mock_result

    client = Neo4jClient(uri="neo4j+s://x", username="u", password="p")
    client._driver = mock_driver

    repo = Neo4jRepository(client)
    res = await repo.get_menu_item("NON_EXIST")
    assert res is None


async def test_network_error_raises_retrieval_error(mock_driver, mock_session):
    mock_driver.session = MagicMock(return_value=mock_session)
    mock_session.__aenter__.return_value = mock_session
    mock_session.run.side_effect = Exception("Connection timeout")

    client = Neo4jClient(uri="neo4j+s://x", username="u", password="p")
    client._driver = mock_driver

    repo = Neo4jRepository(client)
    with pytest.raises(RetrievalError):
        await repo.get_menu_item("M001")
