"""Cypher query templates for Neo4j Aura Graph & Vector RAG."""

# 1. Uniqueness constraints
INIT_CONSTRAINTS = [
    """
    CREATE CONSTRAINT menu_item_id_unique IF NOT EXISTS
    FOR (m:MenuItem)
    REQUIRE m.item_id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT category_name_unique IF NOT EXISTS
    FOR (c:Category)
    REQUIRE c.name IS UNIQUE
    """,
]

# 2. Vector index for MenuItem.embedding (dimension defaults to 768)
INIT_VECTOR_INDEX = """
CREATE VECTOR INDEX menu_vector_index IF NOT EXISTS
FOR (m:MenuItem)
ON (m.embedding)
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 768,
    `vector.similarity_function`: 'cosine'
  }
}
"""

# 3. Upsert MenuItem and connect to Category
UPSERT_MENU_ITEM = """
MERGE (m:MenuItem {item_id: $item_id})
SET m.name = $name_vi,
    m.name_vi = $name_vi,
    m.name_en = $name_en,
    m.category = $category,
    m.category_en = $category_en,
    m.price_s = $price_s,
    m.price_m = $price_m,
    m.price_l = $price_l,
    m.sizes = $sizes,
    m.temperature = $temperature,
    m.caffeine = $caffeine,
    m.vegan = $vegan,
    m.allergens = $allergens,
    m.ingredients = $ingredients,
    m.description_vi = $description_vi,
    m.description_en = $description_en,
    m.embedding = $embedding

MERGE (c:Category {name: $category})
ON CREATE SET c.name_en = $category_en

MERGE (m)-[:BELONGS_TO]->(c)
RETURN m.item_id AS item_id
"""

# 4. Get MenuItem by ID
GET_MENU_ITEM_BY_ID = """
MATCH (m:MenuItem {item_id: $item_id})-[:BELONGS_TO]->(c:Category)
RETURN m {
    .item_id,
    .name_vi,
    .name_en,
    .category,
    .category_en,
    .price_s,
    .price_m,
    .price_l,
    .sizes,
    .temperature,
    .caffeine,
    .vegan,
    .allergens,
    .ingredients,
    .description_vi,
    .description_en
} AS item
"""

# 5. Search MenuItem by text (exact match prioritized over substring match)
SEARCH_MENU_ITEM_BY_TEXT = """
MATCH (m:MenuItem)
WITH m, toLower(trim($query)) AS q, toLower(m.name_vi) AS n_vi, toLower(coalesce(m.name_en, '')) AS n_en
WHERE n_vi = q OR n_en = q OR n_vi CONTAINS q OR q CONTAINS n_vi OR (n_en <> '' AND n_en CONTAINS q)
WITH m,
     CASE
       WHEN n_vi = q OR n_en = q THEN 1.0
       WHEN n_vi CONTAINS q THEN 0.9
       ELSE 0.8
     END AS score,
     abs(size(m.name_vi) - size(trim($query))) AS len_diff
ORDER BY score DESC, len_diff ASC
LIMIT 1
RETURN m {
    .item_id,
    .name_vi,
    .name_en,
    .category,
    .category_en,
    .price_s,
    .price_m,
    .price_l,
    .sizes,
    .temperature,
    .caffeine,
    .vegan,
    .allergens,
    .ingredients,
    .description_vi,
    .description_en
} AS item, score
"""

# 6. Search MenuItem by vector similarity on menu_vector_index
SEARCH_MENU_ITEM_BY_VECTOR = """
CALL db.index.vector.queryNodes('menu_vector_index', $top_k, $embedding)
YIELD node AS m, score
WHERE score >= $min_score
RETURN m {
    .item_id,
    .name_vi,
    .name_en,
    .category,
    .category_en,
    .price_s,
    .price_m,
    .price_l,
    .sizes,
    .temperature,
    .caffeine,
    .vegan,
    .allergens,
    .ingredients,
    .description_vi,
    .description_en
} AS item, score
ORDER BY score DESC
LIMIT 1
"""


