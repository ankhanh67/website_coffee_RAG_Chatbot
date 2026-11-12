from unittest.mock import AsyncMock, MagicMock

from src.rag.ingestion.menu import MenuIngestor, build_menu_item_embedding_text, parse_menu_row
from src.schema.retrieval import MenuItemRecord


def test_parse_menu_row():
    row = {
        "item_id": "M001",
        "name_vi": "Phin Sữa Đá",
        "name_en": "Iced Vietnamese Milk Coffee",
        "category": "Cà phê",
        "category_en": "Coffee",
        "price_s": "33000",
        "price_m": "39000",
        "price_l": "49000",
        "sizes": "S/M/L",
        "temperature": "iced",
        "caffeine": "có",
        "vegan": "không",
        "allergens": "sữa",
        "ingredients": "cà phê phin, sữa đặc, đá",
        "description_vi": "Đậm vị",
        "description_en": "Bold",
    }
    item = parse_menu_row(row)
    assert item.item_id == "M001"
    assert item.price_s == 33000
    assert item.price_m == 39000
    assert item.sizes == ["S", "M", "L"]
    assert item.allergens == ["sữa"]


def test_build_menu_item_embedding_text():
    item = MenuItemRecord(
        item_id="M001",
        name_vi="Phin Sữa Đá",
        name_en="Iced Vietnamese Milk Coffee",
        category="Cà phê",
        category_en="Coffee",
        temperature="iced",
        caffeine="có",
        vegan="không",
        allergens=["sữa"],
        ingredients="cà phê phin, sữa đặc, đá",
        description_vi="Đậm đà",
    )
    text = build_menu_item_embedding_text(item)
    assert "Món: Phin Sữa Đá" in text
    assert "Danh mục: Cà phê" in text
    assert "Dị ứng: sữa" in text


async def test_menu_ingestor_flow(tmp_path):
    csv_file = tmp_path / "menu.csv"
    csv_file.write_text(
        "item_id,name_vi,name_en,category,category_en,price_s,price_m,price_l,sizes,temperature,caffeine,vegan,allergens,ingredients,description_vi,description_en\n"
        "M001,Phin Sữa Đá,Iced Milk Coffee,Cà phê,Coffee,33000,39000,49000,S/M/L,iced,có,không,sữa,cà phê,Đậm,Bold\n"
        "M002,Phin Đen Đá,Iced Black Coffee,Cà phê,Coffee,29000,35000,45000,S/M/L,iced,có,có,không,cà phê,Đắng,Bitter\n",
        encoding="utf-8",
    )

    mock_repo = MagicMock()
    mock_repo.upsert_menu_item = AsyncMock(return_value="OK")

    mock_embeddings = MagicMock()
    mock_embeddings.get_embeddings_batch = AsyncMock(return_value=[[0.1] * 768, [0.2] * 768])

    ingestor = MenuIngestor(
        csv_path=csv_file,
        repository=mock_repo,
        embeddings_client=mock_embeddings,
        batch_size=10,
    )

    count = await ingestor.ingest()
    assert count == 2
    assert mock_embeddings.get_embeddings_batch.await_count == 1
    assert mock_repo.upsert_menu_item.await_count == 2
