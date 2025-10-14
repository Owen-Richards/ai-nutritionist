"""Core database abstractions used across the data access layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Generic, Iterable, List, Optional, Protocol, Sequence, Tuple, TypeVar

__all__ = [
    "DatabaseError",
    "ConnectionPoolError",
    "QueryPerformanceError",
    "Specification",
    "QueryBuilder",
    "Repository",
    "UnitOfWork",
]


class DatabaseError(RuntimeError):
    """Raised when database interaction fails."""


class ConnectionPoolError(DatabaseError):
    """Raised when the connection pool cannot serve a request."""


class QueryPerformanceError(DatabaseError):
    """Raised when a query violates performance guarantees."""


T_co = TypeVar("T_co", covariant=True)
T = TypeVar("T")
ID = TypeVar("ID")


class Specification(Protocol[T_co]):
    """Specification pattern entry point."""

    def is_satisfied_by(self, candidate: T_co) -> bool:  # pragma: no cover - protocol
        ...

    def to_filters(self) -> Dict[str, Any]:  # pragma: no cover - protocol
        ...


@dataclass(frozen=True)
class QueryStep:
    """Represents a step inside a query plan."""

    operation: str
    payload: Dict[str, Any]


class QueryBuilder(Generic[T]):
    """Composable query builder that surfaces intent and metrics."""

    def __init__(self, table: str) -> None:
        self.table = table
        self._steps: List[QueryStep] = []
        self._selected: Sequence[str] | None = None
        self._limit: Optional[int] = None
        self._offset: Optional[int] = None
        self._prefetch: List[str] = []

    # Lightweight comments to help readers understand the mutation intent.
    def select(self, *columns: str) -> "QueryBuilder[T]":
        self._selected = columns or self._selected
        self._steps.append(QueryStep("select", {"columns": columns}))
        return self

    def where(self, **filters: Any) -> "QueryBuilder[T]":
        self._steps.append(QueryStep("where", {"filters": filters}))
        return self

    def join(self, table: str, on: str, kind: str = "inner") -> "QueryBuilder[T]":
        self._steps.append(QueryStep("join", {"table": table, "on": on, "kind": kind}))
        return self

    def order_by(self, *columns: str) -> "QueryBuilder[T]":
        self._steps.append(QueryStep("order_by", {"columns": columns}))
        return self

    def limit(self, value: int) -> "QueryBuilder[T]":
        self._limit = value
        self._steps.append(QueryStep("limit", {"value": value}))
        return self

    def offset(self, value: int) -> "QueryBuilder[T]":
        self._offset = value
        self._steps.append(QueryStep("offset", {"value": value}))
        return self

    def prefetch(self, *relations: str) -> "QueryBuilder[T]":
        if relations:
            self._prefetch.extend(rel for rel in relations if rel not in self._prefetch)
            self._steps.append(QueryStep("prefetch", {"relations": relations}))
        return self

    @property
    def prefetch_relations(self) -> Sequence[str]:
        return tuple(self._prefetch)

    @property
    def steps(self) -> Sequence[QueryStep]:
        return tuple(self._steps)

    def render(self) -> Dict[str, Any]:
        """Produce a representation suitable for logging/monitoring."""
        return {
            "table": self.table,
            "select": self._selected,
            "limit": self._limit,
            "offset": self._offset,
            "prefetch": self.prefetch_relations,
            "plan": [step.__dict__ for step in self._steps],
        }


class Repository(Protocol[T, ID]):
    """Repository contract used by the service layer."""

    def get(self, identifier: ID) -> Optional[T]:  # pragma: no cover - protocol
        ...

    def list(self, *, specification: Optional[Specification[T]] = None, limit: Optional[int] = None) -> Sequence[T]:  # pragma: no cover - protocol
        ...

    def add(self, entity: T) -> ID:  # pragma: no cover - protocol
        ...

    def add_many(self, entities: Iterable[T]) -> Sequence[ID]:  # pragma: no cover - protocol
        ...

    def update(self, entity: T) -> None:  # pragma: no cover - protocol
        ...

    def delete(self, identifier: ID) -> None:  # pragma: no cover - protocol
        ...

    def execute_query(self, builder: QueryBuilder[T]) -> Sequence[T]:  # pragma: no cover - protocol
        ...


class UnitOfWork(Protocol):
    """Unit of Work contract coordinating repositories and transactions."""

    repositories: Dict[str, Repository[Any, Any]]

    def __enter__(self) -> "UnitOfWork":  # pragma: no cover - protocol
        ...

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:  # pragma: no cover - protocol
        ...

    def commit(self) -> None:  # pragma: no cover - protocol
        ...

    def rollback(self) -> None:  # pragma: no cover - protocol
        ...

    def register(self, name: str, repository: Repository[Any, Any]) -> None:  # pragma: no cover - protocol
        ...

