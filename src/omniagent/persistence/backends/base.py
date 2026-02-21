"""Base class for persistence backend adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod

from beanie import Document

from omniagent.db.document_models import DocumentModels


class BackendAdapterBase(ABC):
    """Abstract lifecycle contract for persistence backends."""

    @classmethod
    @abstractmethod
    async def initialize(
        cls,
        db_name: str | None = None,
        srv_uri: str | None = None,
        allow_index_dropping: bool = False,
        models: DocumentModels | None = None,
        extra_document_models: list[type[Document]] | None = None,
    ) -> None:
        ...

    @classmethod
    @abstractmethod
    async def shutdown(cls) -> None:
        ...
