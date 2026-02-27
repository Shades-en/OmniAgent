"""Shared user repository implementation."""

from __future__ import annotations

from dataclasses import dataclass

from omniagent.persistence.contracts import UserRecord
from omniagent.persistence.serializers import user_to_record


@dataclass(slots=True)
class SharedUserRepository:
    user_model: type

    async def get_by_client_id(self, client_id: str) -> UserRecord | None:
        user = await self.user_model.get_by_client_id(client_id=client_id)
        if user is None:
            return None
        return user_to_record(user)

    async def delete_by_client_id(self, client_id: str, cascade: bool = True) -> dict:
        return await self.user_model.delete_by_client_id(client_id=client_id, cascade=cascade)
