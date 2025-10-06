"""Strava adapter stub to ingest cardio workouts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict

from .base import SyncResult, WearableAdapter


class StravaAdapter(WearableAdapter):
    provider_name = "strava"

    async def sync_summary(self, access_token: str) -> SyncResult:
        metrics: Dict[str, float] = {
            "rides": 2,
            "runs": 1,
            "training_load": 45.5,
        }
        metadata = {
            "source": "stub",
            "unit_map": {
                "rides": "count",
                "runs": "count",
                "training_load": "tss",
            },
        }
        return SyncResult(
            provider=self.provider_name,
            synced_at=datetime.now(timezone.utc),
            metrics=metrics,
            metadata=metadata,
        )
