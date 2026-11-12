from pydantic import BaseModel, Field

from src.schema.router import RouterAction


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1)
    message: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    session_id: str
    action: RouterAction
    reply: str

