from __future__ import annotations

from typing import Any, ClassVar, Iterable


class PublicDictMixin:
    """
    Small helper for consistent, JSON-safe serialization of Beanie Documents.

    Uses `model_dump(mode="json")` and a class-level `PUBLIC_EXCLUDE` set for defaults.
    Consumers can pass additional `exclude` fields per call.
    """

    PUBLIC_EXCLUDE: ClassVar[set[str]] = set()

    def to_public_dict(self, *, exclude: set[str] | None = None) -> dict[str, Any]:
        effective_exclude = set(self.PUBLIC_EXCLUDE)
        if exclude:
            effective_exclude |= exclude
        return self.model_dump(mode="json", exclude=effective_exclude)

    @classmethod
    def to_public_dicts(
        cls,
        items: Iterable[PublicDictMixin],
        *,
        exclude: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        return [item.to_public_dict(exclude=exclude) for item in items]

