"""Shared summary repository implementation."""

from __future__ import annotations

from dataclasses import dataclass

from omniagent.persistence.contracts import SummaryRecord
from omniagent.persistence.serializers import summary_to_record


@dataclass(slots=True)
class SharedSummaryRepository:
    summary_model: type

    async def get_latest_by_session(self, session_id: str | None) -> SummaryRecord | None:
        summary = await self.summary_model.get_latest_by_session(session_id=session_id)
        if summary is None:
            return None
        return summary_to_record(summary)

    async def create_with_session(self, session_id: str, summary: SummaryRecord) -> SummaryRecord:
        created = await self.summary_model.create_with_session_id(
            session_id=session_id,
            summary=summary,
        )
        return summary_to_record(created)
