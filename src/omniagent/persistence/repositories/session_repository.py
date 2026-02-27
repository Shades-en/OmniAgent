"""Shared session repository implementation."""

from __future__ import annotations

from dataclasses import dataclass

from omniagent.persistence.contracts import Page, SessionRecord
from omniagent.persistence.serializers import session_to_record


@dataclass(slots=True)
class SharedSessionRepository:
    session_model: type

    async def get_by_id_and_client_id(self, session_id: str, client_id: str) -> SessionRecord | None:
        session = await self.session_model.get_by_id_and_client_id(session_id=session_id, client_id=client_id)
        if session is None:
            return None
        return session_to_record(session)

    async def list_by_client_id(self, client_id: str, page: int, page_size: int) -> Page[SessionRecord]:
        sessions = await self.session_model.get_paginated_by_user_client_id(
            client_id=client_id,
            page=page,
            page_size=page_size,
        )
        total_count = await self.session_model.count_by_user_client_id(client_id=client_id)
        return Page(
            items=[session_to_record(session) for session in sessions],
            total_count=total_count,
            page=page,
            page_size=page_size,
        )

    async def list_all_by_client_id(self, client_id: str) -> list[SessionRecord]:
        sessions = await self.session_model.get_all_by_user_client_id(client_id=client_id)
        return [session_to_record(session) for session in sessions]

    async def rename_by_client_id(self, session_id: str, name: str, client_id: str) -> dict:
        return await self.session_model.update_name_by_client_id(
            session_id=session_id,
            name=name,
            client_id=client_id,
        )

    async def delete_with_related_by_client_id(self, session_id: str, client_id: str) -> dict:
        return await self.session_model.delete_with_related_by_client_id(
            session_id=session_id,
            client_id=client_id,
        )

    async def delete_all_by_client_id(self, client_id: str) -> dict:
        return await self.session_model.delete_all_by_user_client_id(client_id=client_id)
