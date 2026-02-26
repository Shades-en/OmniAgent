"""Mongo summary repository adapter."""

from __future__ import annotations

from dataclasses import dataclass

from beanie import Document
from bson import ObjectId

from omniagent.persistence.contracts import SummaryRecord
from omniagent.persistence.backends.mongo.repositories.serializers import summary_document_to_record


@dataclass(slots=True)
class MongoSummaryRepository:
    summary_model: type[Document]
    session_model: type[Document]

    async def get_latest_by_session(self, session_id: str | None) -> SummaryRecord | None:
        summary = await self.summary_model.get_latest_by_session(session_id=session_id)
        if summary is None:
            return None
        return summary_document_to_record(summary)

    async def create_with_session(self, session_id: str, summary: SummaryRecord) -> SummaryRecord:
        session = await self.session_model.get(ObjectId(session_id))
        if session is None:
            raise ValueError(f"Session not found for summary creation: {session_id}")

        summary_doc = self.summary_model(
            content=summary.content,
            token_count=summary.token_count,
            start_turn_number=summary.start_turn_number,
            end_turn_number=summary.end_turn_number,
        )
        created = await self.summary_model.create_with_session(session=session, summary=summary_doc)
        return summary_document_to_record(created)

