"""MongoDB persistence backend adapter lifecycle."""

from __future__ import annotations

from beanie import Document

from omniagent.db.document_models import DocumentModels
from omniagent.db.mongo import DEFAULT_MODELS, MongoDB
from omniagent.persistence.backends.base import BackendAdapterBase
from omniagent.persistence.model_contracts import validate_document_models, validate_repository_models


class MongoBackendAdapter(BackendAdapterBase):
    """Lifecycle adapter for Mongo persistence initialization and shutdown."""

    @classmethod
    async def initialize(
        cls,
        db_name: str | None = None,
        srv_uri: str | None = None,
        allow_index_dropping: bool = False,
        models: DocumentModels | None = None,
        extra_document_models: list[type[Document]] | None = None,
    ) -> None:
        if models is not None and not isinstance(models, DocumentModels):
            raise TypeError("initialize(models=...) must be a DocumentModels instance.")

        resolved_models = models or DEFAULT_MODELS
        validate_document_models(resolved_models)
        validate_repository_models(resolved_models)

        await MongoDB.init(
            db_name=db_name,
            srv_uri=srv_uri,
            allow_index_dropping=allow_index_dropping,
            models=resolved_models,
            extra_document_models=extra_document_models,
        )

    @classmethod
    async def shutdown(cls) -> None:
        await MongoDB.close()
