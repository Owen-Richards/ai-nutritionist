"""SQL-backed repository helpers with monitoring and caching."""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from ..abstractions import QueryBuilder
from ..cache import QueryCache
from ..connection_pool import ConnectionPool
from ..monitoring import QueryMonitor
from ..optimizations import IndexManager, QueryOptimizer

__all__ = [
    "CompiledQuery",
    "AsyncSqlRepository",
]


@dataclass(slots=True)
class CompiledQuery:
    sql: str
    params: Tuple[Any, ...]
    filters: Sequence[str]
    order: Sequence[str]


class AsyncSqlRepository:
    """Base repository wired with caching, pooling, and monitoring."""

    def __init__(
        self,
        table: str,
        *,
        pool: ConnectionPool,
        primary_key: str = "id",
        monitor: Optional[QueryMonitor] = None,
        cache: Optional[QueryCache] = None,
        optimizer: Optional[QueryOptimizer] = None,
        index_manager: Optional[IndexManager] = None,
    ) -> None:
        self._table = table
        self._pool = pool
        self._pk = primary_key
        self._monitor = monitor
        self._cache = cache
        self._optimizer = optimizer
        self._index_manager = index_manager

    async def fetch_all(self, builder: QueryBuilder[Any], *, expected_rows: Optional[int] = None) -> List[Dict[str, Any]]:
        compiled = self._compile(builder)
        if self._optimizer:
            self._optimizer.optimize(builder, expected_rows=expected_rows)
        cache_key = None
        if self._cache:
            cache_key = QueryCache.make_key(compiled.sql, {"params": compiled.params})
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached
        rows = await self._run_select(compiled, readonly=True)
        if self._cache and cache_key:
            self._cache.set(cache_key, rows)
        return rows

    async def fetch_one(self, builder: QueryBuilder[Any]) -> Optional[Dict[str, Any]]:
        builder.limit(1)
        results = await self.fetch_all(builder, expected_rows=1)
        return results[0] if results else None

    async def insert(self, payload: Dict[str, Any]) -> Any:
        columns = list(payload.keys())
        placeholders = ", ".join(["?"] * len(columns))
        sql = f"INSERT INTO {self._table} ({', '.join(columns)}) VALUES ({placeholders})"
        params = tuple(payload[column] for column in columns)
        return await self._run_write(sql, params)

    async def insert_many(self, payloads: Iterable[Dict[str, Any]]) -> None:
        payloads = list(payloads)
        if not payloads:
            return
        columns = list(payloads[0].keys())
        placeholders = ", ".join(["?"] * len(columns))
        sql = f"INSERT INTO {self._table} ({', '.join(columns)}) VALUES ({placeholders})"
        values = [tuple(payload[column] for column in columns) for payload in payloads]
        await self._run_many(sql, values)

    async def update(self, identifier: Any, updates: Dict[str, Any]) -> None:
        assignments = ", ".join(f"{column} = ?" for column in updates)
        sql = f"UPDATE {self._table} SET {assignments} WHERE {self._pk} = ?"
        params = tuple(updates[column] for column in updates) + (identifier,)
        await self._run_write(sql, params)
        if self._cache:
            self._cache.invalidate(predicate=lambda key, _: True)

    async def delete(self, identifier: Any) -> None:
        sql = f"DELETE FROM {self._table} WHERE {self._pk} = ?"
        params = (identifier,)
        await self._run_write(sql, params)
        if self._cache:
            self._cache.invalidate(predicate=lambda key, _: True)

    async def _run_select(self, compiled: CompiledQuery, *, readonly: bool) -> List[Dict[str, Any]]:
        if self._index_manager and compiled.filters:
            self._index_manager.record_access(self._table, filters=compiled.filters, order_by=compiled.order)

        def _execute() -> List[Dict[str, Any]]:
            start = time.perf_counter()
            with self._pool.get_connection(readonly=readonly, autocommit=True) as connection:
                cursor = connection.execute(compiled.sql, compiled.params)
                records = [dict(row) for row in cursor.fetchall()]
            duration = time.perf_counter() - start
            if self._monitor:
                self._monitor.record(
                    {"sql": compiled.sql, "params": compiled.params},
                    duration=duration,
                    rowcount=len(records),
                    origin=self._table,
                )
            return records

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _execute)

    async def _run_write(self, sql: str, params: Tuple[Any, ...]) -> Any:
        def _execute() -> Any:
            start = time.perf_counter()
            with self._pool.get_connection(readonly=False, autocommit=False) as connection:
                cursor = connection.execute(sql, params)
                connection.commit()
                last_row_id = getattr(cursor, "lastrowid", None)
                rowcount = cursor.rowcount
            duration = time.perf_counter() - start
            if self._monitor:
                self._monitor.record(
                    {"sql": sql, "params": params},
                    duration=duration,
                    rowcount=rowcount,
                    origin=self._table,
                )
            return last_row_id

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _execute)

    async def _run_many(self, sql: str, param_sets: Sequence[Tuple[Any, ...]]) -> None:
        def _execute() -> None:
            start = time.perf_counter()
            with self._pool.get_connection(readonly=False, autocommit=False) as connection:
                connection.executemany(sql, param_sets)
                connection.commit()
            duration = time.perf_counter() - start
            if self._monitor:
                self._monitor.record(
                    {"sql": sql, "batch": len(param_sets)},
                    duration=duration,
                    rowcount=len(param_sets),
                    origin=self._table,
                )

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _execute)

    def _compile(self, builder: QueryBuilder[Any]) -> CompiledQuery:
        plan = builder.render()
        columns = plan.get("select") or ("*",)
        select_clause = ", ".join(columns)
        sql_parts = [f"SELECT {select_clause} FROM {self._table}"]
        params: List[Any] = []
        filters: List[str] = []
        order: List[str] = []
        where_added = False

        for step in builder.steps:
            if step.operation == "join":
                payload = step.payload
                sql_parts.append(f"{payload['kind'].upper()} JOIN {payload['table']} ON {payload['on']}")
            elif step.operation == "where":
                filter_parts = []
                for column, value in step.payload["filters"].items():
                    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
                        placeholders = ", ".join(["?"] * len(value))
                        filter_parts.append(f"{column} IN ({placeholders})")
                        params.extend(value)
                    else:
                        filter_parts.append(f"{column} = ?")
                        params.append(value)
                    filters.append(column)
                if filter_parts:
                    clause = " AND ".join(filter_parts)
                    if where_added:
                        sql_parts.append(f"AND {clause}")
                    else:
                        sql_parts.append(f"WHERE {clause}")
                        where_added = True
            elif step.operation == "order_by":
                order = list(step.payload["columns"])
                if order:
                    sql_parts.append("ORDER BY " + ", ".join(order))
            elif step.operation == "limit":
                sql_parts.append(f"LIMIT {step.payload['value']}")
            elif step.operation == "offset":
                sql_parts.append(f"OFFSET {step.payload['value']}")

        compiled_sql = " ".join(sql_parts)
        return CompiledQuery(sql=compiled_sql, params=tuple(params), filters=tuple(filters), order=tuple(order))

    @staticmethod
    def to_json(value: Any) -> str:
        return json.dumps(value, separators=(",", ":"))

    @staticmethod
    def from_json(value: Optional[str]) -> Any:
        return json.loads(value) if value else None

