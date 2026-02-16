from __future__ import annotations

from dataclasses import dataclass
from typing import Type

from beanie import Document


@dataclass(frozen=True)
class DocumentModels:
    user: Type[Document]
    session: Type[Document]
    summary: Type[Document]
    message: Type[Document]


_DOCUMENT_MODELS: DocumentModels | None = None


def set_document_models(*, user: Type[Document], session: Type[Document], summary: Type[Document], message: Type[Document]) -> None:
    global _DOCUMENT_MODELS
    _DOCUMENT_MODELS = DocumentModels(user=user, session=session, summary=summary, message=message)


def get_document_models() -> DocumentModels:
    if _DOCUMENT_MODELS is None:
        raise RuntimeError("Document models not configured. Call MongoSessionManager.initialize() first.")
    return _DOCUMENT_MODELS


def get_message_model() -> Type[Document]:
    return get_document_models().message


def get_summary_model() -> Type[Document]:
    return get_document_models().summary

