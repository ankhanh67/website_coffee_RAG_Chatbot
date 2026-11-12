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
SET m.name_vi = $name_vi,
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
