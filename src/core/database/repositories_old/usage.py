"""Repository tracking query performance metrics for alerting."""

from __future__ import annotations

import asyncio
import threading
from datetime import datetime
from typing import Any, Dict, List

from ..connection_pool import ConnectionPool
from ..monitoring import QueryEvent, QueryMonitor
from ..cache import QueryCache
from ..optimizations import IndexManager, QueryOptimizer
from .base import AsyncSqlRepository, CompiledQuery

__all__ = ["SqlUsageAnalyticsRepository"]


class SqlUsageAnalyticsRepository(AsyncSqlRepository):
    """Persists aggregated query metrics for dashboards and alerts."""

    _schema_lock = threading.Lock()
    _schema_ready = False

    def __init__(
        self,
        pool: ConnectionPool,
        *,
        monitor: QueryMonitor | None = None,
        cache: QueryCache | None = None,
        optimizer: QueryOptimizer | None = None,
        index_manager: IndexManager | None = None,
    ) -> None:
        super().__init__(
            "query_events",
            pool=pool,
            primary_key="event_id",
            monitor=monitor,
            cache=cache,
            optimizer=optimizer,
            index_manager=index_manager,
        )
        self._ensure_schema(pool)

    @classmethod
    def _ensure_schema(cls, pool: ConnectionPool) -> None:
        if cls._schema_ready:
            return
        with cls._schema_lock:
            if cls._schema_ready:
                return
            with pool.get_connection(readonly=False, autocommit=False) as connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS query_events (
                        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        channel TEXT NOT NULL,
                        locale TEXT,
                        statement TEXT NOT NULL,
                        duration REAL NOT NULL,
                        rowcount INTEGER,
                        recorded_at TEXT NOT NULL,
                        metadata TEXT
                    )
                    """
                )
                connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_query_events_channel_time ON query_events(channel, recorded_at DESC)"
                )
                connection.commit()
            cls._schema_ready = True

    def attach_to_monitor(self, monitor: QueryMonitor, *, channel: str, locale: str | None = None) -> None:
        def _handler(event: QueryEvent) -> None:
            payload = {
                "channel": channel,
                "locale": locale,
                "statement": event.payload.get("sql") or str(event.payload),
                "duration": event.duration,
                "rowcount": event.rowcount,
                "metadata": {
                    "origin": event.origin,
                    "recorded": event.timestamp,
                    "prefetch": event.payload.get("prefetch") if isinstance(event.payload, dict) else None,
                },
            }
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.record_event(**payload))
            except RuntimeError:
                asyncio.run(self.record_event(**payload))

        monitor.register_slow_query_handler(_handler)

    async def record_event(
        self,
        *,
        channel: str,
        statement: str,
        duration: float,
        rowcount: int | None,
        locale: str | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> None:
        await self.insert(
            {
                "channel": channel,
                "locale": locale,
                "statement": statement,
                "duration": duration,
                "rowcount": rowcount,
                "recorded_at": datetime.utcnow().isoformat(),
                "metadata": self.to_json(metadata or {}),
            }
        )

    async def slow_queries(self, *, threshold: float = 0.5, limit: int = 20) -> List[Dict[str, Any]]:
        sql = (
            "SELECT event_id, channel, locale, statement, duration, rowcount, recorded_at, metadata "
            "FROM query_events WHERE duration >= ? ORDER BY duration DESC LIMIT ?"
        )
        compiled = CompiledQuery(sql=sql, params=(threshold, limit), filters=("duration",), order=("duration",))
        records = await self._run_select(compiled, readonly=True)
        for record in records:
            record["metadata"] = self.from_json(record.get("metadata")) or {}
        return records

    async def purge_before(self, iso_timestamp: str) -> None:
        sql = "DELETE FROM query_events WHERE recorded_at < ?"
        await self._run_write(sql, (iso_timestamp,))
