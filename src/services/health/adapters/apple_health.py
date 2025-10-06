"""Apple Health adapter stub with unit normalization."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict

from .base import SyncResult, WearableAdapter


class AppleHealthAdapter(WearableAdapter):
    provider_name = "apple_health"

    async def sync_summary(self, access_token: str) -> SyncResult:
        # Placeholder: in production we'd call Apple HealthKit via user export or HealthKit API proxy
        metrics: Dict[str, float] = {
            "steps": 8500,
            "active_minutes": 42,
            "resting_heart_rate": 58,
        }
        metadata = {
            "source": "stub",
            "unit_map": {
                "steps": "count",
                "active_minutes": "minutes",
                "resting_heart_rate": "bpm",
            },
        }
        return SyncResult(
            provider=self.provider_name,
            synced_at=datetime.now(timezone.utc),
            metrics=metrics,
            metadata=metadata,
        )
