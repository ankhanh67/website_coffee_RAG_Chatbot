"""Pydantic schemas for Neo4j retrieval and graph entities."""

from typing import Any

from pydantic import BaseModel, Field


class MenuItemRecord(BaseModel):
    item_id: str
    name_vi: str
    name_en: str
    category: str
    category_en: str
    price_s: int | None = None
    price_m: int | None = None
    price_l: int | None = None
    sizes: list[str] = Field(default_factory=list)
    temperature: str = "any"
    caffeine: str = "không"
    vegan: str = "không"
    allergens: list[str] = Field(default_factory=list)
    ingredients: str = ""
    description_vi: str = ""
    description_en: str = ""


class VectorSearchResult(BaseModel):
    node_id: str
    score: float
    properties: dict[str, Any] = Field(default_factory=dict)


class ChunkRecord(BaseModel):
    chunk_id: str
    source: str
    title: str
    text: str
    doc_id: str = ""
    order: int = 0
    file: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class EntityRecord(BaseModel):
    name: str
    entity_type: str = "GENERAL"
    canonical_name: str

