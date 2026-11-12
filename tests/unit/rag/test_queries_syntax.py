from src.rag.graph import queries


def test_queries_exist_and_non_empty():
    assert len(queries.INIT_CONSTRAINTS) == 2
    assert "REQUIRE m.item_id IS UNIQUE" in queries.INIT_CONSTRAINTS[0]
    assert "REQUIRE c.name IS UNIQUE" in queries.INIT_CONSTRAINTS[1]

    assert "CREATE VECTOR INDEX" in queries.INIT_VECTOR_INDEX
    assert "menu_vector_index" in queries.INIT_VECTOR_INDEX
    assert "$dimension" in queries.INIT_VECTOR_INDEX or "768" in queries.INIT_VECTOR_INDEX

    assert "$item_id" in queries.UPSERT_MENU_ITEM
    assert "BELONGS_TO" in queries.UPSERT_MENU_ITEM
    assert "$item_id" in queries.GET_MENU_ITEM_BY_ID
