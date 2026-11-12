"""Pydantic schemas for the FAQ flow with grounded source citations."""

from pydantic import BaseModel, Field


class SourceReference(BaseModel):
    source_id: str
    title: str
    snippet: str = ""


class FAQAnswer(BaseModel):
    answer: str
    is_grounded: bool
    grounded_sources: list[SourceReference] = Field(default_factory=list)
