from enum import StrEnum

from pydantic import BaseModel, Field


class RouterAction(StrEnum):
    ORDER = "order"
    CONSULTANT = "consultant"
    FAQ = "faq"
    IGNORE = "ignore"


class RouterDecision(BaseModel):
    action: RouterAction
    confidence: float = Field(ge=0.0, le=1.0)
    probabilities: dict[RouterAction, float] = Field(default_factory=dict)
    is_fallback: bool = False

