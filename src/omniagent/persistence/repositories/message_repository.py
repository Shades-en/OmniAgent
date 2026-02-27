"""Shared message repository implementation."""

from __future__ import annotations

from dataclasses import dataclass

from omniagent.persistence.contracts import MessageRecord, Page
from omniagent.persistence.serializers import message_to_record


@dataclass(slots=True)
class SharedMessageRepository:
    message_model: type

    async def list_by_session(self, session_id: str, page: int, page_size: int) -> Page[MessageRecord]:
        messages = await self.message_model.get_paginated_by_session(
            session_id=session_id,
            page=page,
            page_size=page_size,
        )
        total_count = await self.message_model.count_by_session(session_id=session_id)
        return Page(
            items=[message_to_record(message) for message in messages],
            total_count=total_count,
            page=page,
            page_size=page_size,
        )

    async def list_all_by_session(self, session_id: str) -> list[MessageRecord]:
        messages = await self.message_model.get_all_by_session(session_id=session_id)
        return [message_to_record(message) for message in messages]

    async def delete_by_client_message_id_and_client_id(self, client_message_id: str, client_id: str) -> dict:
        return await self.message_model.delete_by_client_message_id_and_client_id(
            client_message_id,
            client_id=client_id,
        )
