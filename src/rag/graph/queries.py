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
WITH m, toLower(trim($search_text)) AS q, toLower(m.name_vi) AS n_vi, toLower(coalesce(m.name_en, '')) AS n_en
WHERE n_vi = q OR n_en = q OR n_vi CONTAINS q OR q CONTAINS n_vi OR (n_en <> '' AND n_en CONTAINS q)
WITH m,
     CASE
       WHEN n_vi = q OR n_en = q THEN 1.0
       WHEN n_vi CONTAINS q THEN 0.9
       ELSE 0.8
     END AS score,
     abs(size(m.name_vi) - size(trim($search_text))) AS len_diff
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

# 7. Uniqueness constraints for Chunk and Entity
INIT_CHUNK_CONSTRAINTS = [
    """
    CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS
    FOR (c:Chunk)
    REQUIRE c.chunk_id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT entity_canonical_name_unique IF NOT EXISTS
    FOR (e:Entity)
    REQUIRE e.canonical_name IS UNIQUE
    """,
]

# 8. Vector index for Chunk.embedding (dimension defaults to 768)
INIT_CHUNK_VECTOR_INDEX = """
CREATE VECTOR INDEX chunk_vector_index IF NOT EXISTS
FOR (c:Chunk)
ON (c.embedding)
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 768,
    `vector.similarity_function`: 'cosine'
  }
}
"""

# 9. Upsert Chunk
UPSERT_CHUNK = """
MERGE (c:Chunk {chunk_id: $chunk_id})
SET c.source = $source,
    c.title = $title,
    c.text = $text,
    c.doc_id = $doc_id,
    c.order = $order,
    c.file = $file,
    c.metadata = $metadata,
    c.embedding = $embedding
RETURN c.chunk_id AS chunk_id
"""

# 10. Link adjacent Chunks with [:NEXT]
LINK_CHUNKS_NEXT = """
MATCH (c1:Chunk {chunk_id: $c1_id}), (c2:Chunk {chunk_id: $c2_id})
MERGE (c1)-[:NEXT]->(c2)
"""

# 11. Link Chunk to Entity with [:MENTIONS]
LINK_CHUNK_ENTITY_MENTIONS = """
MATCH (c:Chunk {chunk_id: $chunk_id})
MERGE (e:Entity {canonical_name: $canonical_name})
ON CREATE SET e.name = $name, e.type = $entity_type
MERGE (c)-[:MENTIONS]->(e)
"""



