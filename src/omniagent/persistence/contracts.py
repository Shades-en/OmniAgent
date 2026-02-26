"""Portable persistence contracts and DTOs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, Protocol, TypeVar, runtime_checkable


T = TypeVar("T")


@dataclass(slots=True)
class Page(Generic[T]):
    """Generic pagination envelope."""

    items: list[T]
    total_count: int
    page: int
    page_size: int


@dataclass(slots=True)
class UserRecord:
    id: str
    client_id: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SessionRecord:
    id: str
    name: str
    latest_turn_number: int
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class MessageRecord:
    id: str | None
    role: str
    turn_number: int
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SummaryRecord:
    id: str | None
    content: str
    start_turn_number: int
    end_turn_number: int
    token_count: int
    data: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class UserRepository(Protocol):
    async def get_by_client_id(self, client_id: str) -> UserRecord | None:
        ...

    async def delete_by_client_id(self, client_id: str, cascade: bool = True) -> dict:
        ...


@runtime_checkable
class SessionRepository(Protocol):
    async def get_by_id_and_client_id(self, session_id: str, client_id: str) -> SessionRecord | None:
        ...

    async def list_by_client_id(self, client_id: str, page: int, page_size: int) -> Page[SessionRecord]:
        ...

    async def list_all_by_client_id(self, client_id: str) -> list[SessionRecord]:
        ...

    async def rename_by_client_id(self, session_id: str, name: str, client_id: str) -> dict:
        ...

    async def delete_with_related_by_client_id(self, session_id: str, client_id: str) -> dict:
        ...

    async def delete_all_by_client_id(self, client_id: str) -> dict:
        ...


@runtime_checkable
class MessageRepository(Protocol):
    async def list_by_session(self, session_id: str, page: int, page_size: int) -> Page[MessageRecord]:
        ...

    async def list_all_by_session(self, session_id: str) -> list[MessageRecord]:
        ...

    async def delete_by_client_message_id_and_client_id(self, client_message_id: str, client_id: str) -> dict:
        ...


@runtime_checkable
class SummaryRepository(Protocol):
    async def get_latest_by_session(self, session_id: str | None) -> SummaryRecord | None:
        ...

    async def create_with_session(self, session_id: str, summary: SummaryRecord) -> SummaryRecord:
        ...
