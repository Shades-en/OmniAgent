"""Postgres model registry and accessors."""

from __future__ import annotations

from dataclasses import dataclass

from omniagent.schemas.postgres import Message, Session, Summary, User


@dataclass(slots=True)
class PostgresModels:
    """Configured Postgres ORM model bundle."""

    user: type[User]
    session: type[Session]
    summary: type[Summary]
    message: type[Message]


DEFAULT_MODELS = PostgresModels(
    user=User,
    session=Session,
    summary=Summary,
    message=Message,
)

_MODELS: PostgresModels | None = None


def set_postgres_models(models: PostgresModels) -> None:
    global _MODELS
    _MODELS = models


def get_postgres_models() -> PostgresModels:
    if _MODELS is None:
        raise RuntimeError(
            "Postgres models are not initialized. "
            "Call initialize_persistence(backend=PersistenceBackend.POSTGRES, ...) first."
        )
    return _MODELS


def get_user_model() -> type[User]:
    return get_postgres_models().user


def get_session_model() -> type[Session]:
    return get_postgres_models().session


def get_summary_model() -> type[Summary]:
    return get_postgres_models().summary


def get_message_model() -> type[Message]:
    return get_postgres_models().message
