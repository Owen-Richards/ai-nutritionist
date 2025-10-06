"""Registry for dietitian-reviewed response playbooks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class PlaybookEntry:
    condition: str
    language_key: str
    responses: List[str]
    reviewed_by: str
    reviewed_at: datetime
    version: str = "1.0"
    notes: Optional[str] = None


class PlaybookRegistry:
    """Lightweight in-memory registry ensuring compliant responses."""

    def __init__(self) -> None:
        self._playbooks: Dict[str, PlaybookEntry] = {}

    def register(self, entry: PlaybookEntry) -> None:
        self._playbooks[self._key(entry.condition, entry.language_key)] = entry

    def get(self, condition: str, language_key: str = "en") -> Optional[PlaybookEntry]:
        return self._playbooks.get(self._key(condition, language_key))

    @staticmethod
    def _key(condition: str, language_key: str) -> str:
        return f"{condition.lower()}::{language_key.lower()}"
