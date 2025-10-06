"""Garmin Connect adapter stub."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict

from .base import SyncResult, WearableAdapter


class GarminAdapter(WearableAdapter):
    provider_name = "garmin"

    async def sync_summary(self, access_token: str) -> SyncResult:
        metrics: Dict[str, float] = {
            "steps": 9200,
            "active_minutes": 55,
            "floors": 18,
        }
        metadata = {
            "source": "stub",
            "unit_map": {
                "steps": "count",
                "active_minutes": "minutes",
                "floors": "count",
            },
        }
        return SyncResult(
            provider=self.provider_name,
            synced_at=datetime.now(timezone.utc),
            metrics=metrics,
            metadata=metadata,
        )
