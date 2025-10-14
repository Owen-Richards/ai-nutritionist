"""Unit of Work implementation backed by the connection pool."""

from __future__ import annotations

from contextlib import ExitStack
from typing import Any, Callable, Dict, Optional

from .abstractions import Repository, UnitOfWork
from .connection_pool import ConnectionPool

__all__ = ["SqlUnitOfWork"]


class SqlUnitOfWork(UnitOfWork):
    """Coordinates transactional work and repository lifecycle."""

    def __init__(
        self,
        pool: ConnectionPool,
        *,
        readonly: bool = False,
        autocommit: bool = False,
    ) -> None:
        self._pool = pool
        self._readonly = readonly
        self._autocommit = autocommit
        self._stack = ExitStack()
        self._connection: Any = None
        self._committed = False
        self.repositories: Dict[str, Repository[Any, Any]] = {}
        self._factories: Dict[str, Callable[[Any], Repository[Any, Any]]] = {}

    def register_factory(self, name: str, factory: Callable[[Any], Repository[Any, Any]]) -> None:
        self._factories[name] = factory

    def register(self, name: str, repository: Repository[Any, Any]) -> None:
        self.repositories[name] = repository

    def __enter__(self) -> "SqlUnitOfWork":
        self._connection = self._stack.enter_context(
            self._pool.get_connection(readonly=self._readonly, autocommit=self._autocommit)
        )
        for name, factory in self._factories.items():
            self.repositories[name] = factory(self._connection)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc_type is not None:
            self.rollback()
        elif not self._readonly and not self._autocommit and not self._committed:
            self.commit()
        self._stack.close()
        self._connection = None
        self.repositories.clear()

    @property
    def connection(self) -> Any:
        if self._connection is None:
            raise RuntimeError("UnitOfWork connection is not available outside the context")
        return self._connection

    def commit(self) -> None:
        if self._readonly:
            return
        if hasattr(self._connection, "commit"):
            self._connection.commit()
        self._committed = True

    def rollback(self) -> None:
        if hasattr(self._connection, "rollback"):
            self._connection.rollback()
        self._committed = False

