"""Base data source definitions."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List


@dataclass
class SourceData:
    """Container for raw data and metadata from a source."""

    name: str
    scope: str
    endpoint: str
    level: str
    department_code: str
    fetched_at_utc: str
    raw_data: Dict[str, Any]


class DataSource(ABC):
    """Abstract base class for data sources."""

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config

    @abstractmethod
    def fetch_current_data(self) -> List[SourceData]:
        """Fetch current data from configured sources."""

    def get_hashable_content(self, data: Dict[str, Any]) -> bytes:
        """Return canonical JSON bytes for hashing."""
        return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def get_metadata(self) -> Dict[str, Any]:
        """Return metadata about the data source configuration."""
        return {
            "type": self.config.get("type", "unknown"),
            "sources": self.config.get("sources", []),
            "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        }
