from src.schema.retrieval import MenuItemRecord, VectorSearchResult


def test_menu_item_record_valid():
    item = MenuItemRecord(
        item_id="M001",
        name_vi="Phin Sữa Đá",
        name_en="Iced Vietnamese Milk Coffee",
        category="Cà phê",
        category_en="Coffee",
        price_s=33000,
        price_m=39000,
        price_l=49000,
        sizes=["S", "M", "L"],
        temperature="iced",
        caffeine="có",
        vegan="không",
        allergens=["sữa"],
        ingredients="cà phê phin, sữa đặc, đá",
        description_vi="Đậm đà",
        description_en="Bold",
    )
    assert item.item_id == "M001"
    assert item.price_m == 39000
    assert isinstance(item.price_m, int)
    assert "sữa" in item.allergens


def test_vector_search_result_valid():
    res = VectorSearchResult(node_id="M001", score=0.92, properties={"name_vi": "Phin Sữa Đá"})
    assert res.score == 0.92
    assert res.properties["name_vi"] == "Phin Sữa Đá"
