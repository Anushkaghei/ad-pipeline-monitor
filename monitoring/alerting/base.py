"""Abstract base class for alert channels."""

from abc import ABC, abstractmethod

from monitoring.models import Alert


class AlertChannel(ABC):
    """Base class for all alert dispatch channels."""

    @abstractmethod
    def send(self, alert: Alert) -> bool:
        """
        Send an alert through this channel.
        Returns True if successful, False otherwise.
        """
        ...

    @property
    @abstractmethod
    def channel_name(self) -> str:
        """Return the channel identifier."""
        ...

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if this channel has valid credentials."""
        ...
