"""SQL implementation of the UserRepository interface with optimisations."""

from __future__ import annotations

import threading
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from packages.core.src.interfaces.repositories import UserRepository

from ..abstractions import QueryBuilder
from ..cache import QueryCache
from ..connection_pool import ConnectionPool
from ..monitoring import QueryMonitor
from ..optimizations import IndexManager, QueryOptimizer
from .base import AsyncSqlRepository

__all__ = ["SqlUserRepository"]


class SqlUserRepository(AsyncSqlRepository, UserRepository):
    """SQLite-backed user repository with caching and monitoring."""

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
            "users",
            pool=pool,
            primary_key="user_id",
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
                    CREATE TABLE IF NOT EXISTS users (
                        user_id TEXT PRIMARY KEY,
                        phone_number TEXT UNIQUE NOT NULL,
                        document TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                    """
                )
                connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone_number)"
                )
                connection.commit()
            cls._schema_ready = True

    async def get_user_by_phone(self, phone_number: str) -> Optional[Dict[str, Any]]:
        builder = QueryBuilder("users").select("user_id", "phone_number", "document").where(
            phone_number=self._normalize_phone(phone_number)
        )
        record = await self.fetch_one(builder)
        return self._deserialize(record) if record else None

    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        phone_number = self._normalize_phone(user_data["phone_number"])
        existing = await self.get_user_by_phone(phone_number)
        if existing:
            return existing

        now = datetime.utcnow().isoformat()
        user_id = user_data.get("user_id", str(uuid4()))
        document = dict(user_data)
        document["user_id"] = user_id
        document["phone_number"] = phone_number
        document.setdefault("created_at", now)
        document.setdefault("last_active", now)

        await self.insert(
            {
                "user_id": user_id,
                "phone_number": phone_number,
                "document": self.to_json(document),
                "created_at": now,
                "updated_at": now,
            }
        )
        if self._cache:
            self._cache.invalidate(predicate=lambda key, _: "users" in key)
        return document

    async def update_user(self, phone_number: str, updates: Dict[str, Any]) -> bool:
        existing = await self.get_user_by_phone(phone_number)
        if not existing:
            return False
        now = datetime.utcnow().isoformat()
        document = {**existing, **updates}
        document["last_active"] = now

        await self.update(
            document["user_id"],
            {
                "document": self.to_json(document),
                "updated_at": now,
            },
        )
        if self._cache:
            self._cache.invalidate(predicate=lambda key, _: "users" in key)
        return True

    async def get_user_preferences(self, phone_number: str) -> Dict[str, Any]:
        existing = await self.get_user_by_phone(phone_number)
        if not existing:
            return {}
        return {
            "dietary_restrictions": existing.get("dietary_restrictions", []),
            "health_goals": existing.get("health_goals", []),
            "allergies": existing.get("allergies", []),
            "dislikes": existing.get("dislikes", []),
            "max_prep_time": existing.get("max_prep_time", 45),
            "calorie_target": existing.get("calorie_target"),
            "budget_preference": existing.get("budget_preference", "medium"),
        }

    def _deserialize(self, record: Dict[str, Any]) -> Dict[str, Any]:
        document = self.from_json(record.get("document")) or {}
        document.setdefault("user_id", record.get("user_id"))
        document.setdefault("phone_number", record.get("phone_number"))
        return document

    @staticmethod
    def _normalize_phone(phone_number: str) -> str:
        return "".join(ch for ch in phone_number if ch.isdigit())

