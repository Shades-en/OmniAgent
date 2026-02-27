"""Postgres session model."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from sqlalchemy import ForeignKey, Integer, String, delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, mapped_column, relationship

from omniagent.config import (
    DEFAULT_SESSION_NAME,
    DEFAULT_SESSION_PAGE_SIZE,
)
from omniagent.db.postgres.engine import get_sessionmaker
from omniagent.exceptions import (
    MessageCreationError,
    SessionCreationError,
    SessionDeletionError,
    SessionRetrievalError,
    SessionUpdateError,
)
from omniagent.schemas.postgres.base import PostgresBase
from omniagent.schemas.postgres.mixins import CreatedAtMixin, UpdatedAtMixin, utc_now
from omniagent.schemas.postgres.public_dict import PublicDictMixin
from omniagent.schemas.postgres.user import User
from omniagent.types.message import MessageDTO

if TYPE_CHECKING:
    from omniagent.schemas.postgres.message import Message
    from omniagent.schemas.postgres.summary import Summary


class Session(PublicDictMixin, CreatedAtMixin, UpdatedAtMixin, PostgresBase):
    """Session ORM model."""

    __tablename__ = "sessions"
    PUBLIC_EXCLUDE: ClassVar[set[str]] = {"user_id"}

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default=DEFAULT_SESSION_NAME)
    latest_turn_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    user: Mapped[User] = relationship(back_populates="sessions")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )
    summaries: Mapped[list["Summary"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )

    def to_public_dict(self, *, exclude: set[str] | None = None) -> dict[str, Any]:
        data = super().to_public_dict(exclude=exclude)
        data["id"] = self.id
        return data

    @classmethod
    async def get_by_id(cls, session_id: str) -> Session | None:
        try:
            sessionmaker = get_sessionmaker()
            async with sessionmaker() as db_session:
                return await db_session.get(cls, session_id)
        except Exception as exc:
            raise SessionRetrievalError(
                "Failed to retrieve session by ID",
                details=f"session_id={session_id}, error={exc}",
            ) from exc

    @classmethod
    async def get_by_id_and_client_id(cls, session_id: str, client_id: str) -> Session | None:
        try:
            sessionmaker = get_sessionmaker()
            async with sessionmaker() as session:
                result = await session.execute(
                    select(cls)
                    .join(User, cls.user_id == User.id)
                    .where(cls.id == session_id, User.client_id == client_id)
                )
                return result.scalar_one_or_none()
        except Exception as exc:
            raise SessionRetrievalError(
                "Failed to retrieve session by ID and client_id",
                details=f"session_id={session_id}, client_id={client_id}, error={exc}",
            ) from exc

    @classmethod
    async def create_with_user(
        cls,
        client_id: str,
        session_id: str,
        session_name: str = DEFAULT_SESSION_NAME,
    ) -> Session:
        if not session_id:
            raise SessionCreationError(
                "session_id is required to create a session",
                details="session_id parameter must be provided",
            )

        sessionmaker = get_sessionmaker()
        async with sessionmaker.begin() as session:
            try:
                user = User(client_id=client_id)
                session.add(user)
                await session.flush()

                new_session = cls(
                    id=session_id,
                    name=session_name or DEFAULT_SESSION_NAME,
                    user_id=user.id,
                    latest_turn_number=0,
                )
                session.add(new_session)
                await session.flush()
                await session.refresh(new_session)
                return new_session
            except IntegrityError:
                existing_user = (
                    await session.execute(select(User).where(User.client_id == client_id))
                ).scalar_one_or_none()
                if existing_user is None:
                    raise
                new_session = cls(
                    id=session_id,
                    name=session_name or DEFAULT_SESSION_NAME,
                    user_id=existing_user.id,
                    latest_turn_number=0,
                )
                session.add(new_session)
                await session.flush()
                await session.refresh(new_session)
                return new_session
            except Exception as exc:
                raise SessionCreationError(
                    "Failed to create session with user",
                    details=(
                        f"client_id={client_id}, session_id={session_id}, "
                        f"session_name={session_name}, error={exc}"
                    ),
                ) from exc

    @classmethod
    async def create_for_existing_user(
        cls,
        user: User,
        session_id: str,
        session_name: str = DEFAULT_SESSION_NAME,
    ) -> Session:
        if not session_id:
            raise SessionCreationError(
                "session_id is required to create a session",
                details="session_id parameter must be provided",
            )

        sessionmaker = get_sessionmaker()
        async with sessionmaker.begin() as session:
            try:
                user_row = (
                    await session.execute(select(User).where(User.id == user.id))
                ).scalar_one_or_none()
                if user_row is None:
                    raise SessionCreationError(
                        "Cannot create session for missing user",
                        details=f"user_id={user.id}",
                    )

                new_session = cls(
                    id=session_id,
                    name=session_name or DEFAULT_SESSION_NAME,
                    user_id=user_row.id,
                    latest_turn_number=0,
                )
                session.add(new_session)
                await session.flush()
                await session.refresh(new_session)
                return new_session
            except SessionCreationError:
                raise
            except Exception as exc:
                raise SessionCreationError(
                    "Failed to create session for existing user",
                    details=f"user_id={getattr(user, 'id', None)}, session_id={session_id}, error={exc}",
                ) from exc

    @classmethod
    async def update_name_by_client_id(cls, session_id: str, name: str, client_id: str) -> dict:
        sessionmaker = get_sessionmaker()
        async with sessionmaker.begin() as session:
            try:
                row = (
                    await session.execute(
                        select(cls)
                        .join(User, cls.user_id == User.id)
                        .where(cls.id == session_id, User.client_id == client_id)
                    )
                ).scalar_one_or_none()

                if row is None:
                    return {
                        "session_updated": False,
                        "session_id": session_id,
                        "name": name,
                    }

                row.name = name
                row.updated_at = utc_now()
                return {
                    "session_updated": True,
                    "session_id": session_id,
                    "name": name,
                }
            except Exception as exc:
                raise SessionUpdateError(
                    "Failed to update session name",
                    details=f"session_id={session_id}, name={name}, client_id={client_id}, error={exc}",
                ) from exc

    @classmethod
    async def delete_with_related_by_client_id(cls, session_id: str, client_id: str) -> dict:
        from omniagent.schemas.postgres.message import Message
        from omniagent.schemas.postgres.summary import Summary

        sessionmaker = get_sessionmaker()
        async with sessionmaker.begin() as session:
            try:
                session_row = (
                    await session.execute(
                        select(cls)
                        .join(User, cls.user_id == User.id)
                        .where(cls.id == session_id, User.client_id == client_id)
                    )
                ).scalar_one_or_none()

                if session_row is None:
                    return {
                        "messages_deleted": 0,
                        "summaries_deleted": 0,
                        "session_deleted": False,
                    }

                message_result = await session.execute(
                    delete(Message).where(Message.session_id == session_row.id)
                )
                summary_result = await session.execute(
                    delete(Summary).where(Summary.session_id == session_row.id)
                )
                await session.execute(delete(cls).where(cls.id == session_row.id))

                return {
                    "messages_deleted": message_result.rowcount or 0,
                    "summaries_deleted": summary_result.rowcount or 0,
                    "session_deleted": True,
                }
            except Exception as exc:
                raise SessionDeletionError(
                    "Failed to delete session with related documents",
                    details=f"session_id={session_id}, client_id={client_id}, error={exc}",
                ) from exc

    @classmethod
    async def delete_all_by_user_client_id(cls, client_id: str) -> dict:
        from omniagent.schemas.postgres.message import Message
        from omniagent.schemas.postgres.summary import Summary

        sessionmaker = get_sessionmaker()
        async with sessionmaker.begin() as session:
            try:
                user = (
                    await session.execute(select(User).where(User.client_id == client_id))
                ).scalar_one_or_none()
                if user is None:
                    return {
                        "sessions_deleted": 0,
                        "messages_deleted": 0,
                        "summaries_deleted": 0,
                    }

                session_ids = (
                    await session.execute(select(cls.id).where(cls.user_id == user.id))
                ).scalars().all()
                if not session_ids:
                    return {
                        "sessions_deleted": 0,
                        "messages_deleted": 0,
                        "summaries_deleted": 0,
                    }

                message_result = await session.execute(
                    delete(Message).where(Message.session_id.in_(session_ids))
                )
                summary_result = await session.execute(
                    delete(Summary).where(Summary.session_id.in_(session_ids))
                )
                session_result = await session.execute(delete(cls).where(cls.id.in_(session_ids)))

                return {
                    "sessions_deleted": session_result.rowcount or 0,
                    "messages_deleted": message_result.rowcount or 0,
                    "summaries_deleted": summary_result.rowcount or 0,
                }
            except Exception as exc:
                raise SessionDeletionError(
                    "Failed to delete all sessions for user",
                    details=f"client_id={client_id}, error={exc}",
                ) from exc

    @classmethod
    async def get_paginated_by_user_client_id(
        cls,
        client_id: str,
        page: int = 1,
        page_size: int = DEFAULT_SESSION_PAGE_SIZE,
    ) -> list[Session]:
        try:
            offset = (page - 1) * page_size
            sessionmaker = get_sessionmaker()
            async with sessionmaker() as session:
                result = await session.execute(
                    select(cls)
                    .join(User, cls.user_id == User.id)
                    .where(User.client_id == client_id)
                    .order_by(cls.updated_at.desc())
                    .offset(offset)
                    .limit(page_size)
                )
                return list(result.scalars().all())
        except Exception as exc:
            raise SessionRetrievalError(
                "Failed to retrieve paginated sessions for user by client_id",
                details=f"client_id={client_id}, page={page}, page_size={page_size}, error={exc}",
            ) from exc

    @classmethod
    async def count_by_user_client_id(cls, client_id: str) -> int:
        try:
            sessionmaker = get_sessionmaker()
            async with sessionmaker() as session:
                result = await session.execute(
                    select(func.count(cls.id))
                    .join(User, cls.user_id == User.id)
                    .where(User.client_id == client_id)
                )
                return int(result.scalar_one() or 0)
        except Exception as exc:
            raise SessionRetrievalError(
                "Failed to count sessions for user by client_id",
                details=f"client_id={client_id}, error={exc}",
            ) from exc

    @classmethod
    async def get_all_by_user_client_id(cls, client_id: str) -> list[Session]:
        try:
            sessionmaker = get_sessionmaker()
            async with sessionmaker() as session:
                result = await session.execute(
                    select(cls)
                    .join(User, cls.user_id == User.id)
                    .where(User.client_id == client_id)
                    .order_by(cls.updated_at.desc())
                )
                return list(result.scalars().all())
        except Exception as exc:
            raise SessionRetrievalError(
                "Failed to retrieve all sessions for user by client_id",
                details=f"client_id={client_id}, error={exc}",
            ) from exc

    async def insert_messages(
        self,
        messages: list[MessageDTO],
        turn_number: int,
        previous_summary: Any | None,
    ) -> list["Message"]:
        if not self.id:
            raise MessageCreationError(
                "Cannot insert messages for unsaved session",
                details="Session must be saved to database before inserting messages",
            )

        if not messages:
            return []

        try:
            from omniagent.db.postgres import get_message_model

            message_model = get_message_model()
            previous_summary_id = getattr(previous_summary, "id", None)

            def _serialize_parts(parts: list[Any]) -> list[dict[str, Any]]:
                serialized: list[dict[str, Any]] = []
                for part in parts:
                    if hasattr(part, "model_dump"):
                        serialized.append(part.model_dump(mode="json"))
                    elif isinstance(part, dict):
                        serialized.append(part)
                return serialized

            rows = [
                message_model(
                    role=msg.role.value if hasattr(msg.role, "value") else str(msg.role),
                    metadata_json=msg.metadata,
                    parts=_serialize_parts(msg.parts),
                    turn_number=turn_number,
                    session_id=self.id,
                    previous_summary_id=previous_summary_id,
                    created_at=msg.created_at,
                    client_message_id=msg.id,
                )
                for msg in messages
            ]

            sessionmaker = get_sessionmaker()
            async with sessionmaker.begin() as session:
                session.add_all(rows)
                session_row = await session.get(Session, self.id)
                if session_row is None:
                    raise SessionUpdateError(
                        "Session not found while inserting messages",
                        details=f"session_id={self.id}",
                    )
                session_row.latest_turn_number = turn_number
                session_row.updated_at = utc_now()

            return rows
        except Exception as exc:
            raise MessageCreationError(
                "Failed to bulk insert messages for session",
                details=f"session_id={self.id}, turn_number={turn_number}, message_count={len(messages)}, error={exc}",
            ) from exc


__all__ = ["Session"]
