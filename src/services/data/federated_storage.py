"""Federated storage tier connecting transactional, time-series, and knowledge stores."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from packages.core.src.entities.user import UserProfile

@dataclass
class StorageConnector:
    name: str
    kind: str  # transactional, timeseries, document, graph
    client: Any

    def write(self, payload: Dict[str, Any]) -> None:  # pragma: no cover - interface stub
        self.client.write(payload)


class FederatedHealthStorage:
    """Coordinates writes across dedicated data stores with consent checks."""

    def __init__(self) -> None:
        self._connectors: Dict[str, StorageConnector] = {}

    def register_connector(self, connector: StorageConnector) -> None:
        self._connectors[connector.kind] = connector

    def record_conversation(self, user_profile: UserProfile, payload: Dict[str, Any]) -> None:
        if not self._is_consent_granted(user_profile, "personalization"):
            return
        transactional = self._connectors.get("transactional")
        if transactional:
            transactional.write(payload)

    def record_biometrics(self, user_profile: UserProfile, payload: Dict[str, Any]) -> None:
        if not self._is_consent_granted(user_profile, "research"):
            return
        timeseries = self._connectors.get("timeseries")
        if timeseries:
            record = {**payload, "recorded_at": datetime.utcnow().isoformat()}
            timeseries.write(record)

    def register_playbook(self, payload: Dict[str, Any]) -> None:
        document = self._connectors.get("document")
        if document:
            document.write(payload)

    def relate_health_fact(self, payload: Dict[str, Any]) -> None:
        graph = self._connectors.get("graph")
        if graph:
            graph.write(payload)

    @staticmethod
    def _is_consent_granted(user_profile: UserProfile, consent_key: str) -> bool:
        if not user_profile.consent_flags:
            return False
        return user_profile.consent_flags.get(consent_key, False)
