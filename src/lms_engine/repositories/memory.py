"""In-memory repositories for the LMS engine."""

from __future__ import annotations

from typing import Dict, Generic, Iterable, List, Optional, TypeVar


T = TypeVar("T")


class InMemoryRepository(Generic[T]):
    def __init__(self) -> None:
        self._items: Dict[str, T] = {}

    def add(self, item: T) -> T:
        self._items[getattr(item, "id")] = item
        return item

    def get(self, item_id: str) -> Optional[T]:
        return self._items.get(item_id)

    def list(self) -> List[T]:
        return list(self._items.values())

    def all(self) -> Iterable[T]:
        return self._items.values()


class LearningPathRepository(InMemoryRepository[T]):
    def get_by_role(self, role_id: str) -> Optional[T]:
        for item in self._items.values():
            if getattr(item, "role_id") == role_id:
                return item
        return None
