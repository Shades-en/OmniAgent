"""Postgres declarative base."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class PostgresBase(DeclarativeBase):
    """Base SQLAlchemy declarative model for Postgres schemas."""

    pass
