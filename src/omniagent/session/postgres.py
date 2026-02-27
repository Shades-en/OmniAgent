"""Postgres-specific SessionManager implementation using SQLAlchemy ORM."""

from __future__ import annotations

from omniagent.db.postgres import (
    get_message_model,
    get_session_model,
    get_summary_model,
    get_user_model,
)
from omniagent.session.base import SessionManager


class PostgresSessionManager(SessionManager):
    """Postgres implementation of SessionManager."""

    @classmethod
    def _get_message_model(cls):
        return get_message_model()

    @classmethod
    def _get_summary_model(cls):
        return get_summary_model()

    @classmethod
    def _get_session_model(cls):
        return get_session_model()

    @classmethod
    def _get_user_model(cls):
        return get_user_model()
