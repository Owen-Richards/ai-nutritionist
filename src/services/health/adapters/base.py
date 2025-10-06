"""Base adapter for wearable integrations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional


@dataclass
class SyncResult:
    """Outcome of a wearable sync operation."""

    provider: str
    synced_at: datetime
    metrics: Dict[str, float]
    metadata: Dict[str, object]


class WearableAdapter:
    """Defines the interface for wearable providers."""

    provider_name: str = "unknown"

    def __init__(self, *, timeout_seconds: int = 12) -> None:
        self._timeout_seconds = timeout_seconds

    async def refresh(self, access_token: str, refresh_token: Optional[str] = None) -> str:
        """Refresh tokens when required (noop by default)."""
        return access_token

    async def sync_summary(self, access_token: str) -> SyncResult:
        """Pull lightweight summary metrics from the wearable provider."""
        raise NotImplementedError
