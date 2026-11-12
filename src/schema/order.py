"""Pydantic schemas for the Order flow. All VND amounts use int (never float)."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class OrderIntentType(StrEnum):
    ADD = "add"
    REMOVE = "remove"
    UPDATE = "update"
    CONFIRM = "confirm"
    CANCEL = "cancel"


class OrderItemInput(BaseModel):
    name: str = Field(min_length=1)
    size: Literal["S", "M", "L"] = "M"
    quantity: int = Field(default=1, gt=0)
    note: str = ""


class MenuMatch(BaseModel):
    item_id: str
    name_vi: str
    size: Literal["S", "M", "L"]
    unit_price_vnd: int = Field(ge=0)
    quantity: int = Field(gt=0)

    @property
    def line_total_vnd(self) -> int:
        return self.unit_price_vnd * self.quantity


class OrderCalculation(BaseModel):
    items: list[MenuMatch] = Field(default_factory=list)
    subtotal_vnd: int = Field(default=0, ge=0)
    discount_vnd: int = Field(default=0, ge=0)
    total_vnd: int = Field(default=0, ge=0)
    unmatched_items: list[str] = Field(default_factory=list)

