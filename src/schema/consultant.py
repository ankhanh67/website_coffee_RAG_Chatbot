"""Pydantic schemas for the Consultant (recommendation) flow."""

from typing import Literal

from pydantic import BaseModel, Field


class ConsultantFilter(BaseModel):
    max_price_vnd: int | None = Field(default=None, gt=0)
    temperature: Literal["hot", "iced", "any"] = "any"
    has_caffeine: bool | None = None
    vegan_only: bool = False
    exclude_allergens: list[str] = Field(default_factory=list)
    taste_preferences: list[str] = Field(default_factory=list)
