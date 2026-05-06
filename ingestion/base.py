"""Abstract base class for ad platform adapters."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass
class IngestionResult:
    """Result from an ingestion operation."""

    platform: str
    entity_type: str
    rows_fetched: int
    date_range: tuple[date, date] | None = None
    data: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    success: bool = True


class AdPlatformAdapter(ABC):
    """
    Abstract base class for ad platform API adapters.

    All adapters (real and mock) implement this interface so the
    ingestion pipeline can swap between them transparently.
    """

    @abstractmethod
    def fetch_campaigns(
        self, date_start: date, date_end: date
    ) -> IngestionResult:
        """Fetch campaign-level performance data."""
        ...

    @abstractmethod
    def fetch_adsets(
        self, date_start: date, date_end: date
    ) -> IngestionResult:
        """Fetch adset / ad-group level data."""
        ...

    @abstractmethod
    def fetch_keywords(
        self, date_start: date, date_end: date
    ) -> IngestionResult:
        """Fetch keyword-level data (Google only; Meta returns empty)."""
        ...

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return the platform identifier (e.g. 'meta', 'google')."""
        ...
