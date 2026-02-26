"""Shared Mongo document serializers for repository adapters."""

from __future__ import annotations

from typing import Any

from omniagent.persistence.contracts import (
    MessageRecord,
    SessionRecord,
    SummaryRecord,
    UserRecord,
)
from omniagent.utils.general import iso_or_empty


def user_document_to_record(user: Any) -> UserRecord:
    payload = user.to_public_dict() if hasattr(user, "to_public_dict") else user.model_dump(mode="json")
    return UserRecord(
        id=str(getattr(user, "id", payload.get("id", ""))),
        client_id=str(getattr(user, "client_id", payload.get("client_id", ""))),
        data=payload,
    )


def session_document_to_record(session: Any) -> SessionRecord:
    payload = session.to_public_dict() if hasattr(session, "to_public_dict") else session.model_dump(
        mode="json",
        exclude={"user"},
    )
    payload.setdefault("created_at", iso_or_empty(getattr(session, "created_at", None)))
    payload.setdefault("updated_at", iso_or_empty(getattr(session, "updated_at", None)))
    return SessionRecord(
        id=str(getattr(session, "id", payload.get("id", ""))),
        name=str(getattr(session, "name", payload.get("name", ""))),
        latest_turn_number=int(getattr(session, "latest_turn_number", payload.get("latest_turn_number", 0))),
        data=payload,
    )


def message_document_to_record(message: Any) -> MessageRecord:
    payload = message.to_public_dict() if hasattr(message, "to_public_dict") else message.model_dump(mode="json")
    message_id = getattr(message, "client_message_id", None) or payload.get("id")
    return MessageRecord(
        id=str(message_id) if message_id is not None else None,
        role=str(getattr(message, "role", payload.get("role", ""))),
        turn_number=int(getattr(message, "turn_number", payload.get("turn_number", 0))),
        data=payload,
    )


def summary_document_to_record(summary: Any) -> SummaryRecord:
    payload = summary.to_public_dict() if hasattr(summary, "to_public_dict") else summary.model_dump(mode="json")
    payload.setdefault("created_at", iso_or_empty(getattr(summary, "created_at", None)))
    summary_id = getattr(summary, "id", None) or payload.get("id")
    return SummaryRecord(
        id=str(summary_id) if summary_id is not None else None,
        content=str(getattr(summary, "content", payload.get("content", ""))),
        start_turn_number=int(getattr(summary, "start_turn_number", payload.get("start_turn_number", 0))),
        end_turn_number=int(getattr(summary, "end_turn_number", payload.get("end_turn_number", 0))),
        token_count=int(getattr(summary, "token_count", payload.get("token_count", 0))),
        data=payload,
    )

