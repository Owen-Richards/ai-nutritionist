"""Connection pooling and configuration for database access."""

from __future__ import annotations

import sqlite3
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from queue import Empty, Queue
from typing import Any, Callable, Dict, Iterator, Optional, Sequence

from .abstractions import ConnectionPoolError, DatabaseError

__all__ = ["DatabaseConfig", "ConnectionPool"]


@dataclass(slots=True)
class DatabaseConfig:
    """Runtime configuration for a database backend."""

    dsn: str
    driver: str = "sqlite"
    min_size: int = 1
    max_size: int = 10
    pool_timeout: float = 5.0
    connect_args: Dict[str, Any] = field(default_factory=dict)
    read_replicas: Sequence[str] = ()

    def as_dict(self) -> Dict[str, Any]:
        return {
            "dsn": self.dsn,
            "driver": self.driver,
            "min_size": self.min_size,
            "max_size": self.max_size,
            "pool_timeout": self.pool_timeout,
            "connect_args": dict(self.connect_args),
            "read_replicas": list(self.read_replicas),
        }


class ConnectionPool:
    """Simple connection pool with read-replica awareness."""

    def __init__(
        self,
        config: DatabaseConfig,
        *,
        replica_configs: Optional[Sequence[DatabaseConfig]] = None,
        connect_factory: Optional[Callable[[DatabaseConfig], Any]] = None,
    ) -> None:
        self._config = config
        self._connect_factory = connect_factory or self._default_factory
        self._primary = Queue(maxsize=config.max_size)
        self._replicas: Sequence[Queue] = tuple(
            self._build_pool(replica, connect_factory) for replica in (replica_configs or [])
        )
        self._replica_lock = threading.Lock()
        self._replica_index = 0
        self._init_pool(self._primary, config)

    def _build_pool(self, config: DatabaseConfig, factory: Optional[Callable[[DatabaseConfig], Any]]) -> Queue:
        pool = Queue(maxsize=config.max_size)
        self._init_pool(pool, config, factory)
        return pool

    def _init_pool(
        self,
        pool: Queue,
        config: DatabaseConfig,
        factory: Optional[Callable[[DatabaseConfig], Any]] = None,
    ) -> None:
        connector = factory or self._connect_factory
        for _ in range(config.min_size):
            pool.put_nowait(connector(config))

    def _default_factory(self, config: DatabaseConfig) -> Any:
        if config.driver == "sqlite":
            conn = sqlite3.connect(config.dsn, **config.connect_args)
            conn.row_factory = sqlite3.Row
            return conn
        raise DatabaseError(f"Unsupported driver: {config.driver}")

    @contextmanager
    def get_connection(
        self,
        *,
        readonly: bool = False,
        timeout: Optional[float] = None,
        autocommit: bool = True,
    ) -> Iterator[Any]:
        pool = self._select_pool(readonly)
        start = time.perf_counter()
        try:
            conn = pool.get(timeout=timeout or self._config.pool_timeout)
        except Empty as exc:
            raise ConnectionPoolError("Connection pool exhausted") from exc

        try:
            yield conn
            if hasattr(conn, "commit") and not readonly and autocommit:
                conn.commit()
        except Exception:
            if hasattr(conn, "rollback"):
                conn.rollback()
            raise
        finally:
            elapsed = time.perf_counter() - start
            self._check_roundtrip(elapsed)
            try:
                pool.put_nowait(conn)
            except Exception as exc:  # pragma: no cover - defensive
                if hasattr(conn, "close"):
                    conn.close()
                raise ConnectionPoolError("Failed to return connection to pool") from exc

    def _select_pool(self, readonly: bool) -> Queue:
        if readonly and self._replicas:
            with self._replica_lock:
                pool = self._replicas[self._replica_index]
                self._replica_index = (self._replica_index + 1) % len(self._replicas)
            return pool
        return self._primary

    def _check_roundtrip(self, elapsed: float) -> None:
        if elapsed > self._config.pool_timeout * 4:
            raise ConnectionPoolError(f"Connection checkout exceeded threshold: {elapsed:.2f}s")

    def stats(self) -> Dict[str, Any]:
        """Return current pool utilisation statistics."""
        primary_available = self._primary.qsize()
        primary_in_use = self._config.max_size - primary_available
        replicas = [
            {
                "available": pool.qsize(),
                "max_size": self._config.max_size,
            }
            for pool in self._replicas
        ]
        return {
            "primary": {
                "available": primary_available,
                "in_use": primary_in_use,
                "max_size": self._config.max_size,
            },
            "replicas": replicas,
        }

    def close(self) -> None:
        self._drain(self._primary)
        for pool in self._replicas:
            self._drain(pool)

    def _drain(self, pool: Queue) -> None:
        while not pool.empty():
            conn = pool.get_nowait()
            try:
                close = getattr(conn, "close", None)
                if close:
                    close()
            finally:
                pool.task_done()

