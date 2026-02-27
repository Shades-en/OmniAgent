"""Shared record-construction and serialization helpers."""

from __future__ import annotations

from typing import Any

from omniagent.persistence.contracts import MessageRecord, SessionRecord, SummaryRecord, UserRecord
from omniagent.utils.general import iso_or_empty, to_json_safe


def build_user_record(*, user: Any, payload: dict[str, Any]) -> UserRecord:
    normalized_payload = to_json_safe(payload)
    return UserRecord(
        id=str(getattr(user, "id", normalized_payload.get("id", ""))),
        client_id=str(getattr(user, "client_id", normalized_payload.get("client_id", ""))),
        data=normalized_payload,
    )


def build_session_record(*, session: Any, payload: dict[str, Any]) -> SessionRecord:
    payload.setdefault("created_at", iso_or_empty(getattr(session, "created_at", None)))
    payload.setdefault("updated_at", iso_or_empty(getattr(session, "updated_at", None)))
    normalized_payload = to_json_safe(payload)
    return SessionRecord(
        id=str(getattr(session, "id", normalized_payload.get("id", ""))),
        name=str(getattr(session, "name", normalized_payload.get("name", ""))),
        latest_turn_number=int(
            getattr(session, "latest_turn_number", normalized_payload.get("latest_turn_number", 0))
        ),
        data=normalized_payload,
    )


def build_message_record(*, message: Any, payload: dict[str, Any]) -> MessageRecord:
    normalized_payload = to_json_safe(payload)
    message_id = getattr(message, "client_message_id", None) or normalized_payload.get("id")
    return MessageRecord(
        id=str(message_id) if message_id is not None else None,
        role=str(getattr(message, "role", normalized_payload.get("role", ""))),
        turn_number=int(getattr(message, "turn_number", normalized_payload.get("turn_number", 0))),
        data=normalized_payload,
    )


def build_summary_record(*, summary: Any, payload: dict[str, Any]) -> SummaryRecord:
    payload.setdefault("created_at", iso_or_empty(getattr(summary, "created_at", None)))
    normalized_payload = to_json_safe(payload)
    summary_id = getattr(summary, "id", None) or normalized_payload.get("id")
    return SummaryRecord(
        id=str(summary_id) if summary_id is not None else None,
        content=str(getattr(summary, "content", normalized_payload.get("content", ""))),
        start_turn_number=int(
            getattr(summary, "start_turn_number", normalized_payload.get("start_turn_number", 0))
        ),
        end_turn_number=int(getattr(summary, "end_turn_number", normalized_payload.get("end_turn_number", 0))),
        token_count=int(getattr(summary, "token_count", normalized_payload.get("token_count", 0))),
        data=normalized_payload,
    )


def _extract_public_payload(
    entity: Any,
    fallback_exclude: set[str] | None = None,
) -> dict[str, Any]:
    if hasattr(entity, "to_public_dict"):
        payload = entity.to_public_dict()
    elif hasattr(entity, "model_dump"):
        payload = entity.model_dump(mode="json", exclude=fallback_exclude)
    else:
        raise TypeError(
            f"Entity of type {type(entity).__name__} must provide to_public_dict() or model_dump()."
        )

    if not isinstance(payload, dict):
        raise TypeError(
            f"Serialized payload for {type(entity).__name__} must be a dictionary, got {type(payload).__name__}."
        )
    return payload


def user_to_record(entity: Any) -> UserRecord:
    payload = _extract_public_payload(entity)
    return build_user_record(user=entity, payload=payload)


def session_to_record(entity: Any) -> SessionRecord:
    payload = _extract_public_payload(entity, fallback_exclude={"user", "user_id"})
    return build_session_record(session=entity, payload=payload)


def message_to_record(entity: Any) -> MessageRecord:
    payload = _extract_public_payload(entity)
    return build_message_record(message=entity, payload=payload)


def summary_to_record(entity: Any) -> SummaryRecord:
    payload = _extract_public_payload(entity)
    return build_summary_record(summary=entity, payload=payload)


__all__ = [
    "user_to_record",
    "session_to_record",
    "message_to_record",
    "summary_to_record",
]
