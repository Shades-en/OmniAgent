"""Postgres user model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Integer, String, delete, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from omniagent.db.postgres.engine import get_sessionmaker
from omniagent.exceptions import UserDeletionError, UserRetrievalError
from omniagent.types.user import UserType

from omniagent.schemas.postgres.base import PostgresBase
from omniagent.schemas.postgres.mixins import CreatedAtMixin
from omniagent.schemas.postgres.public_dict import PublicDictMixin

if TYPE_CHECKING:
    from omniagent.schemas.postgres.session import Session


class User(PublicDictMixin, CreatedAtMixin, PostgresBase):
    """User ORM model."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    category: Mapped[str] = mapped_column(String(32), default=UserType.GUEST.value, nullable=False)

    sessions: Mapped[list["Session"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    @classmethod
    async def get_by_client_id(cls, client_id: str) -> User | None:
        try:
            sessionmaker = get_sessionmaker()
            async with sessionmaker() as session:
                result = await session.execute(select(cls).where(cls.client_id == client_id))
                return result.scalar_one_or_none()
        except Exception as exc:
            raise UserRetrievalError(
                "Failed to retrieve user by client ID",
                details=f"client_id={client_id}, error={exc}",
            ) from exc

    @classmethod
    async def delete_by_client_id(cls, client_id: str, cascade: bool = True) -> dict:
        from omniagent.schemas.postgres.message import Message
        from omniagent.schemas.postgres.session import Session
        from omniagent.schemas.postgres.summary import Summary

        sessionmaker = get_sessionmaker()
        async with sessionmaker.begin() as session:
            try:
                user = (
                    await session.execute(select(cls).where(cls.client_id == client_id))
                ).scalar_one_or_none()
                if user is None:
                    return {
                        "user_deleted": False,
                        "sessions_deleted": 0,
                        "messages_deleted": 0,
                        "summaries_deleted": 0,
                    }

                session_ids = (
                    await session.execute(select(Session.id).where(Session.user_id == user.id))
                ).scalars().all()

                messages_deleted = 0
                summaries_deleted = 0
                sessions_deleted = 0

                if cascade and session_ids:
                    # Keep these sequential: SQLAlchemy AsyncSession does not support
                    # concurrent execute() calls on the same session/transaction.
                    message_result = await session.execute(
                        delete(Message).where(Message.session_id.in_(session_ids))
                    )
                    summary_result = await session.execute(
                        delete(Summary).where(Summary.session_id.in_(session_ids))
                    )
                    messages_deleted = message_result.rowcount or 0
                    summaries_deleted = summary_result.rowcount or 0

                if session_ids:
                    sessions_result = await session.execute(
                        delete(Session).where(Session.id.in_(session_ids))
                    )
                    sessions_deleted = sessions_result.rowcount or 0

                await session.delete(user)
                return {
                    "user_deleted": True,
                    "sessions_deleted": sessions_deleted,
                    "messages_deleted": messages_deleted,
                    "summaries_deleted": summaries_deleted,
                }
            except Exception as exc:
                raise UserDeletionError(
                    "Failed to delete user by client ID",
                    details=f"client_id={client_id}, cascade={cascade}, error={exc}",
                ) from exc


__all__ = ["User"]
