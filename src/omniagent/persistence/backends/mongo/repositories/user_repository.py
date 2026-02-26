"""Mongo user repository adapter."""

from __future__ import annotations

from dataclasses import dataclass

from beanie import Document

from omniagent.persistence.contracts import UserRecord
from omniagent.persistence.backends.mongo.repositories.serializers import user_document_to_record


@dataclass(slots=True)
class MongoUserRepository:
    user_model: type[Document]

    async def get_by_client_id(self, client_id: str) -> UserRecord | None:
        user = await self.user_model.get_by_client_id(client_id=client_id)
        if user is None:
            return None
        return user_document_to_record(user)

    async def delete_by_client_id(self, client_id: str, cascade: bool = True) -> dict:
        return await self.user_model.delete_by_client_id(client_id=client_id, cascade=cascade)

