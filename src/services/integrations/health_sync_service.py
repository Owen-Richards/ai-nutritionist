"""Service orchestrating wearable adapters, analytics, and federated storage."""

from __future__ import annotations

from typing import Dict

from packages.core.src.entities.user import UserProfile, WearableIntegrationfrom services.analytics_service.src.application.analytics_service import AnalyticsServicefrom src.services.data.federated_storage import FederatedHealthStorage
from src.services.health.adapters import SyncResult, WearableAdapter


class HealthSyncService:
    """Coordinates wearable data ingestion with consent and analytics."""

    def __init__(
        self,
        adapters: Dict[str, WearableAdapter],
        analytics_service: AnalyticsService,
        storage: FederatedHealthStorage,
    ) -> None:
        self._adapters = adapters
        self._analytics = analytics_service
        self._storage = storage

    async def sync_user(self, user_profile: UserProfile) -> Dict[str, SyncResult]:
        results: Dict[str, SyncResult] = {}
        for provider, integration in user_profile.wearable_integrations.items():
            if not self._is_consented(user_profile, provider):
                continue
            adapter = self._adapters.get(provider)
            if not adapter:
                continue
            refreshed_token = await adapter.refresh(integration.access_token, integration.refresh_token)
            sync_result = await adapter.sync_summary(refreshed_token)
            results[provider] = sync_result
            user_profile.register_wearable(
                WearableIntegration(
                    provider=provider,
                    external_user_id=integration.external_user_id,
                    access_token=refreshed_token,
                    refresh_token=integration.refresh_token,
                    expires_at=integration.expires_at,
                    scopes=integration.scopes,
                    last_sync_at=sync_result.synced_at,
                    consent_scopes=integration.consent_scopes,
                )
            )
            await self._analytics.track_wearable_sync(
                user_profile.user_id,
                provider=provider,
                metrics=sync_result.metrics,
                synced_at=sync_result.synced_at,
                context=self._analytics.build_enriched_context(),
            )
            self._storage.record_biometrics(
                user_profile,
                {
                    "provider": provider,
                    "metrics": sync_result.metrics,
                    "metadata": sync_result.metadata,
                    "synced_at": sync_result.synced_at.isoformat(),
                },
            )
        return results

    @staticmethod
    def _is_consented(user_profile: UserProfile, provider: str) -> bool:
        key = f"wearable_{provider}"
        if not user_profile.consent_flags:
            return False
        return user_profile.consent_flags.get(key, False)
