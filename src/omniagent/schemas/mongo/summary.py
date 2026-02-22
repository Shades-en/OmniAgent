from __future__ import annotations

from beanie import Document, Link
from opentelemetry.trace import SpanKind
import pymongo
from bson import ObjectId

from datetime import datetime, timezone
from pydantic import Field
from typing import TYPE_CHECKING, Self, ClassVar
from pydantic import model_validator

from omniagent.tracing import trace_method

from omniagent.exceptions import (
    SummaryRetrievalError,
    SummaryCreationError,
)
from omniagent.utils.general import get_token_count
from omniagent.schemas.mongo.public_dict import PublicDictMixin

if TYPE_CHECKING:
    from omniagent.schemas.mongo.session import Session

class Summary(PublicDictMixin, Document):
    PUBLIC_EXCLUDE: ClassVar[set[str]] = {"session"}

    content: str
    token_count: int = Field(default=0)
    start_turn_number: int
    end_turn_number: int
    session: Link["Session"] | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    @model_validator(mode="after")
    def compute_token_count(self) -> Self:
        """Compute token count from content if not explicitly provided."""
        if self.token_count == 0 and self.content:
            self.token_count = get_token_count(self.content)
        return self

    class Settings:
        name = "summaries"
        indexes = [
            [("session.$id", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)]
        ]
    
    @classmethod
    async def get_latest_by_session(cls, session_id: str | None) -> Summary | None:
        """Retrieve the latest summary for a session, ordered by created_at descending."""
        if not session_id:
            return None
        
        try:
            return await cls.find(
                cls.session.id == ObjectId(session_id)
            ).sort(-cls.created_at).first_or_none()
        except Exception as e:
            raise SummaryRetrievalError(
                "Failed to retrieve latest summary by session ID",
                details=f"session_id={session_id}, error={str(e)}"
            )

    @classmethod
    @trace_method(
        kind=SpanKind.INTERNAL,
        graph_node_id="db_insert_summary",
        capture_input=False,
        capture_output=False
    )
    async def create_with_session(cls, session: "Session", summary: "Summary") -> "Summary":
        """Create a new summary for a session."""
        try:
            summary.session = session
            await summary.insert()
            return summary
        except Exception as e:
            raise SummaryCreationError(
                "Failed to create summary for session",
                details=f"session_id={session.id}, summary={summary}, error={str(e)}"
            )
