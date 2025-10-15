import asyncio
import time
from pathlib import Path

import pytest

from src.core.database import (
    DatabaseConfig,
    ConnectionPool,
    QueryMonitor,
    QueryCache,
    QueryOptimizer,
    IndexManager,
)
from src.core.database.repositories import (
    SqlMealPlanRepository,
    SqlUsageAnalyticsRepository,
    SqlUserRepository,
)
from src.core.database.optimizations import SlowQueryDetector


@pytest.fixture()
def db_pool(tmp_path: Path) -> ConnectionPool:
    db_path = tmp_path / "test.db"
    return ConnectionPool(DatabaseConfig(dsn=str(db_path), min_size=1, max_size=2))


@pytest.mark.asyncio
async def test_user_repository_crud(db_pool: ConnectionPool) -> None:
    cache = QueryCache()
    monitor = QueryMonitor(slow_threshold=5.0)
    optimizer = QueryOptimizer(cache=cache, monitor=monitor)
    users = SqlUserRepository(
        db_pool,
        cache=cache,
        monitor=monitor,
        optimizer=optimizer,
        index_manager=IndexManager(),
    )

    created = await users.create_user({"phone_number": "+1 (555) 123-4567", "dietary_restrictions": ["vegan"]})
    assert created["phone_number"] == "15551234567"
    assert created["dietary_restrictions"] == ["vegan"]

    fetched = await users.get_user_by_phone("+1 555 123 4567")
    assert fetched
    assert fetched["dietary_restrictions"] == ["vegan"]

    updated = await users.update_user("+1 555 123 4567", {"budget_preference": "low"})
    assert updated is True

    refreshed = await users.get_user_by_phone("+15551234567")
    assert refreshed["budget_preference"] == "low"


@pytest.mark.asyncio
async def test_meal_plan_repository(db_pool: ConnectionPool) -> None:
    plans = SqlMealPlanRepository(db_pool, cache=QueryCache())

    base_plan = {"user_id": "user-1", "plan_date": "2024-05-01", "meals": ["salad", "soup"]}
    saved = await plans.save_plan(base_plan)
    assert saved["plan_id"]

    fetched = await plans.get_plan(user_id="user-1", plan_date="2024-05-01")
    assert fetched
    assert fetched["meals"] == ["salad", "soup"]

    await plans.save_plan({**base_plan, "meals": ["salad", "pasta"]})
    history = await plans.list_recent_plans("user-1")
    assert history[0]["meals"] == ["salad", "pasta"]


@pytest.mark.asyncio
async def test_usage_repository_records_slow_queries(db_pool: ConnectionPool) -> None:
    monitor = QueryMonitor(slow_threshold=0.01)
    usage_repo = SqlUsageAnalyticsRepository(db_pool)
    usage_repo.attach_to_monitor(monitor, channel="web", locale="en-US")
    SlowQueryDetector(monitor, threshold=0.01)

    monitor.record({"sql": "SELECT 1"}, duration=0.02, rowcount=1, origin="unit-test")
    await asyncio.sleep(0.05)

    slow = await usage_repo.slow_queries(threshold=0.0)
    assert slow
    assert slow[0]["statement"] == "SELECT 1"

