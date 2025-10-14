import asyncio
from datetime import datetime

import pytest

from services.orchestration.next_best_action import NextBestActionService


@pytest.mark.asyncio
async def test_next_best_action_includes_deep_link_and_cache() -> None:
    service = NextBestActionService()
    now = datetime(2025, 1, 5, 12, 0)

    payload = {
        "user_id": "user-123",
        "channel": "sms",
        "locale": "en-US",
        "timezone": "UTC",
        "user_name": "Alex",
        "diet": "balanced",
        "allergies": ["peanut"],
        "goal": "adherence",
        "plan_day": 3,
        "streak": 2,
        "tokens": 18,
        "quiet_hours": {"start": "22:00", "end": "06:00"},
        "recent_actions": [
            {
                "id": "evt-1",
                "type": "meal_log",
                "timestamp": now.isoformat(),
            }
        ],
        "cost_flags": {"limit_reached": False},
        "plan_status": {"generated_at": now.isoformat()},
        "channel_preferences": ["sms"],
        "feature_flags": {"unified_orchestration": True},
        "initiated_by_user": True,
    }

    decision = await service.select_action(payload)

    assert decision["journey"]
    assert decision["cta_label"]
    assert "utm_source=sms" in decision["deep_link"]
    assert "utm_campaign" in decision["deep_link"]
    assert decision["metadata"]["analytics_tags"]["journey"] == decision["journey"]

    cached = await service.select_action(payload)
    assert cached["metadata"].get("cache_hit") is True
