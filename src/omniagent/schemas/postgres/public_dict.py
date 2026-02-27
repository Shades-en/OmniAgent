"""Public serialization mixins for Postgres models."""

from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar, Iterable


class PublicDictMixin:
    """Mixin providing public dictionary serialization helpers."""

    PUBLIC_EXCLUDE: ClassVar[set[str]] = set()

    def to_public_dict(self, *, exclude: set[str] | None = None) -> dict[str, Any]:
        excluded = set(self.PUBLIC_EXCLUDE)
        if exclude:
            excluded.update(exclude)

        data: dict[str, Any] = {}
        for column_attr in self.__mapper__.column_attrs:
            attr_key = column_attr.key
            column = column_attr.columns[0]
            payload_key = column.name
            if payload_key in excluded or attr_key in excluded:
                continue
            value = getattr(self, attr_key)
            if isinstance(value, datetime):
                data[payload_key] = value.isoformat()
            else:
                data[payload_key] = value
        return data

    @classmethod
    def to_public_dicts(cls, rows: Iterable["PublicDictMixin"]) -> list[dict[str, Any]]:
        return [row.to_public_dict() for row in rows]
