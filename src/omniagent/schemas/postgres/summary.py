"""Postgres summary model."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from sqlalchemy import ForeignKey, Integer, Text, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from omniagent.db.postgres.engine import get_sessionmaker
from omniagent.domain_protocols import SummaryProtocol
from omniagent.exceptions import SummaryCreationError, SummaryRetrievalError
from omniagent.schemas.postgres.base import PostgresBase
from omniagent.schemas.postgres.mixins import CreatedAtMixin
from omniagent.schemas.postgres.public_dict import PublicDictMixin

if TYPE_CHECKING:
    from omniagent.schemas.postgres.session import Session


class Summary(PublicDictMixin, CreatedAtMixin, PostgresBase):
    """Summary ORM model."""

    __tablename__ = "summaries"
    PUBLIC_EXCLUDE: ClassVar[set[str]] = {"session_id"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    start_turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    end_turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)

    session: Mapped["Session"] = relationship(back_populates="summaries")

    @classmethod
    async def get_latest_by_session(cls, session_id: str | None) -> Summary | None:
        if not session_id:
            return None

        try:
            sessionmaker = get_sessionmaker()
            async with sessionmaker() as session:
                result = await session.execute(
                    select(cls)
                    .where(cls.session_id == session_id)
                    .order_by(cls.created_at.desc())
                    .limit(1)
                )
                return result.scalar_one_or_none()
        except Exception as exc:
            raise SummaryRetrievalError(
                "Failed to retrieve latest summary by session ID",
                details=f"session_id={session_id}, error={exc}",
            ) from exc

    @classmethod
    async def create_with_session_id(
        cls,
        session_id: str,
        summary: SummaryProtocol,
    ) -> Summary:
        try:
            summary_row = cls(
                content=summary.content,
                token_count=summary.token_count,
                start_turn_number=summary.start_turn_number,
                end_turn_number=summary.end_turn_number,
                session_id=session_id,
            )

            sessionmaker = get_sessionmaker()
            async with sessionmaker.begin() as db_session:
                db_session.add(summary_row)
                await db_session.flush()
                await db_session.refresh(summary_row)
            return summary_row
        except Exception as exc:
            raise SummaryCreationError(
                "Failed to create summary for session",
                details=f"session_id={session_id}, error={exc}",
            ) from exc


__all__ = ["Summary"]
