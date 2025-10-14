"""Repository for persisting meal plan data and retrieval."""

from __future__ import annotations

import threading
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..abstractions import QueryBuilder
from ..cache import QueryCache
from ..connection_pool import ConnectionPool
from ..monitoring import QueryMonitor
from ..optimizations import IndexManager, QueryOptimizer
from .base import AsyncSqlRepository

__all__ = ["SqlMealPlanRepository"]


class SqlMealPlanRepository(AsyncSqlRepository):
    """Stores generated meal plans with batching-friendly access patterns."""

    _schema_lock = threading.Lock()
    _schema_ready = False

    def __init__(
        self,
        pool: ConnectionPool,
        *,
        monitor: Optional[QueryMonitor] = None,
        cache: Optional[QueryCache] = None,
        optimizer: Optional[QueryOptimizer] = None,
        index_manager: Optional[IndexManager] = None,
    ) -> None:
        super().__init__(
            "meal_plans",
            pool=pool,
            primary_key="plan_id",
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
                    CREATE TABLE IF NOT EXISTS meal_plans (
                        plan_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        plan_date TEXT NOT NULL,
                        document TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                    """
                )
                connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_meal_plans_user_date ON meal_plans(user_id, plan_date DESC)"
                )
                connection.commit()
            cls._schema_ready = True

    async def save_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        plan_id = plan.get("plan_id", str(uuid4()))
        user_id = plan["user_id"]
        plan_date = plan.get("plan_date") or datetime.utcnow().date().isoformat()
        now = datetime.utcnow().isoformat()

        existing = await self.get_plan(user_id=user_id, plan_date=plan_date)
        document = self.to_json({**plan, "plan_id": plan_id, "plan_date": plan_date})

        if existing:
            await self.update(
                existing["plan_id"],
                {
                    "document": document,
                    "updated_at": now,
                },
            )
            result = {**existing, **plan, "plan_id": existing["plan_id"], "updated_at": now}
        else:
            await self.insert(
                {
                    "plan_id": plan_id,
                    "user_id": user_id,
                    "plan_date": plan_date,
                    "document": document,
                    "created_at": now,
                    "updated_at": now,
                }
            )
            result = {**plan, "plan_id": plan_id, "plan_date": plan_date, "created_at": now, "updated_at": now}
        if self._cache:
            self._cache.invalidate(predicate=lambda key, _: "meal_plans" in key)
        return result

    async def get_plan(self, *, user_id: str, plan_date: str) -> Optional[Dict[str, Any]]:
        builder = (
            QueryBuilder("meal_plans")
            .select("plan_id", "user_id", "plan_date", "document", "created_at", "updated_at")
            .where(user_id=user_id, plan_date=plan_date)
            .order_by("updated_at DESC")
        )
        record = await self.fetch_one(builder)
        return self._deserialize(record) if record else None

    async def list_recent_plans(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        builder = (
            QueryBuilder("meal_plans")
            .select("plan_id", "user_id", "plan_date", "document", "created_at", "updated_at")
            .where(user_id=user_id)
            .order_by("plan_date DESC")
            .limit(limit)
        )
        records = await self.fetch_all(builder, expected_rows=limit)
        return [self._deserialize(record) for record in records]

    def _deserialize(self, record: Dict[str, Any]) -> Dict[str, Any]:
        payload = self.from_json(record.get("document")) or {}
        payload.setdefault("plan_id", record.get("plan_id"))
        payload.setdefault("user_id", record.get("user_id"))
        payload.setdefault("plan_date", record.get("plan_date"))
        payload.setdefault("created_at", record.get("created_at"))
        payload.setdefault("updated_at", record.get("updated_at"))
        return payload

