from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Literal


class ChatRequestOptions(BaseModel):
    api_type: Literal["responses", "chat_completion"] = Field(default="responses")


class MessageQuery(BaseModel):
    id: str | None = None
    query: str
