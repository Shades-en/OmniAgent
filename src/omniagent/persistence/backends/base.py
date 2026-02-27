"""Base class for persistence backend adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from omniagent.persistence.context import PersistenceContext


class BackendAdapterBase(ABC):
    """Abstract lifecycle contract for persistence backends."""

    @classmethod
    @abstractmethod
    async def initialize(
        cls,
        config: Any,
    ) -> PersistenceContext:
        ...

    @classmethod
    @abstractmethod
    async def shutdown(cls) -> None:
        ...
