"""Postgres message model."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from omniagent.config import DEFAULT_MESSAGE_PAGE_SIZE, MAX_TURNS_TO_FETCH
from omniagent.db.postgres.engine import get_sessionmaker
from omniagent.exceptions import MessageDeletionError, MessageRetrievalError
from omniagent.schemas.postgres.base import PostgresBase
from omniagent.schemas.postgres.mixins import CreatedAtMixin
from omniagent.schemas.postgres.public_dict import PublicDictMixin
from omniagent.types.message import MessageDTO, Role

if TYPE_CHECKING:
    from omniagent.schemas.postgres.session import Session
    from omniagent.schemas.postgres.summary import Summary


class Message(PublicDictMixin, CreatedAtMixin, PostgresBase):
    """Message ORM model."""

    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("session_id", "client_message_id", name="uq_messages_session_client_message_id"),
    )
    PUBLIC_EXCLUDE: ClassVar[set[str]] = {
        "session_id",
        "previous_summary_id",
        "client_message_id",
    }

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    previous_summary_id: Mapped[int | None] = mapped_column(
        ForeignKey("summaries.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    parts: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True)
    client_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    session: Mapped["Session"] = relationship(back_populates="messages")
    previous_summary: Mapped["Summary | None"] = relationship()

    @property
    def token_count(self) -> int:
        total = 0
        for part in self.parts or []:
            if not isinstance(part, dict):
                continue
            if isinstance(part.get("token_count"), int):
                total += int(part["token_count"])
            else:
                total += int(part.get("input_token_count", 0) or 0)
                total += int(part.get("output_token_count", 0) or 0)
        return total

    def to_public_dict(self, *, exclude: set[str] | None = None) -> dict[str, Any]:
        data = super().to_public_dict(exclude=exclude)
        data["id"] = self.client_message_id
        data["role"] = self.role
        return data

    def to_dto(self) -> MessageDTO:
        role = Role(self.role) if self.role in {member.value for member in Role} else Role.AI
        return MessageDTO(
            id=self.client_message_id,
            role=role,
            parts=self.parts,
            metadata=self.metadata_json or {},
            created_at=self.created_at,
        )

    @classmethod
    def to_dtos(cls, messages: list[Message]) -> list[MessageDTO]:
        return [message.to_dto() for message in messages]

    @classmethod
    async def get_paginated_by_session(
        cls,
        session_id: str,
        page: int = 1,
        page_size: int = DEFAULT_MESSAGE_PAGE_SIZE,
    ) -> list[Message]:
        try:
            offset = (page - 1) * page_size
            sessionmaker = get_sessionmaker()
            async with sessionmaker() as session:
                result = await session.execute(
                    select(cls)
                    .where(cls.session_id == session_id)
                    .order_by(cls.created_at.desc(), cls.role.asc())
                    .offset(offset)
                    .limit(page_size)
                )
                rows = list(result.scalars().all())
                rows.reverse()
                return rows
        except Exception as exc:
            raise MessageRetrievalError(
                "Failed to retrieve paginated messages for session",
                details=f"session_id={session_id}, page={page}, page_size={page_size}, error={exc}",
            ) from exc

    @classmethod
    async def count_by_session(cls, session_id: str) -> int:
        try:
            sessionmaker = get_sessionmaker()
            async with sessionmaker() as session:
                result = await session.execute(select(func.count(cls.id)).where(cls.session_id == session_id))
                return int(result.scalar_one() or 0)
        except Exception as exc:
            raise MessageRetrievalError(
                "Failed to count messages for session",
                details=f"session_id={session_id}, error={exc}",
            ) from exc

    @classmethod
    async def get_all_by_session(cls, session_id: str) -> list[Message]:
        try:
            sessionmaker = get_sessionmaker()
            async with sessionmaker() as session:
                result = await session.execute(
                    select(cls)
                    .where(cls.session_id == session_id)
                    .order_by(cls.created_at.asc(), cls.role.desc())
                )
                return list(result.scalars().all())
        except Exception as exc:
            raise MessageRetrievalError(
                "Failed to retrieve all messages for session",
                details=f"session_id={session_id}, error={exc}",
            ) from exc

    @classmethod
    async def get_latest_by_session(
        cls,
        session_id: str | None,
        current_turn_number: int,
        max_turns: int = MAX_TURNS_TO_FETCH,
    ) -> list[Message]:
        if not session_id:
            return []

        try:
            min_turn_number = max(1, current_turn_number - max_turns)
            sessionmaker = get_sessionmaker()
            async with sessionmaker() as session:
                result = await session.execute(
                    select(cls)
                    .where(
                        cls.session_id == session_id,
                        cls.turn_number >= min_turn_number,
                    )
                    .order_by(cls.created_at.asc())
                )
                return list(result.scalars().all())
        except Exception as exc:
            raise MessageRetrievalError(
                "Failed to retrieve latest messages for session",
                details=f"session_id={session_id}, max_turns={max_turns}, current_turn_number={current_turn_number}, error={exc}",
            ) from exc

    @classmethod
    async def get_by_client_message_id_and_client_id(
        cls,
        client_message_id: str,
        client_id: str,
    ) -> Message | None:
        from omniagent.schemas.postgres.session import Session
        from omniagent.schemas.postgres.user import User

        try:
            sessionmaker = get_sessionmaker()
            async with sessionmaker() as session:
                result = await session.execute(
                    select(cls)
                    .join(Session, cls.session_id == Session.id)
                    .join(User, Session.user_id == User.id)
                    .where(
                        cls.client_message_id == client_message_id,
                        User.client_id == client_id,
                    )
                )
                return result.scalar_one_or_none()
        except Exception as exc:
            raise MessageRetrievalError(
                "Failed to retrieve message by client_message_id and client_id",
                details=f"client_message_id={client_message_id}, client_id={client_id}, error={exc}",
            ) from exc

    @classmethod
    async def delete_by_client_message_id_and_client_id(
        cls,
        client_message_id: str,
        client_id: str,
    ) -> dict:
        from omniagent.schemas.postgres.session import Session
        from omniagent.schemas.postgres.user import User

        try:
            sessionmaker = get_sessionmaker()
            async with sessionmaker.begin() as session:
                message = (
                    await session.execute(
                        select(cls)
                        .join(Session, cls.session_id == Session.id)
                        .join(User, Session.user_id == User.id)
                        .where(
                            cls.client_message_id == client_message_id,
                            User.client_id == client_id,
                        )
                    )
                ).scalar_one_or_none()

                if message is None:
                    return {
                        "message_deleted": False,
                        "deleted_count": 0,
                    }

                await session.delete(message)
                return {
                    "message_deleted": True,
                    "deleted_count": 1,
                }
        except Exception as exc:
            raise MessageDeletionError(
                "Failed to delete message by client_message_id and client_id",
                details=f"client_message_id={client_message_id}, client_id={client_id}, error={exc}",
            ) from exc


__all__ = ["Message"]
