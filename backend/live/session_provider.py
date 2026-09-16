from abc import ABC, abstractmethod
from typing import Optional
from .models import DashboardFrame, PlaybackState


class SessionDataProvider(ABC):
    """
    Abstract base class defining the contract for both Replay and Live session data providers.
    Ensures seamless interchangeability between static replay and live telemetry streams.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize data source (e.g., load cached session slice or connect to live API)."""
        pass

    @abstractmethod
    async def get_current_frame(self) -> DashboardFrame:
        """Produce the current standardized dashboard snapshot frame."""
        pass

    @abstractmethod
    async def play(self) -> None:
        """Resume playback or live ingestion."""
        pass

    @abstractmethod
    async def pause(self) -> None:
        """Pause playback or live ingestion."""
        pass

    @abstractmethod
    async def seek(self, target_iso_time: str) -> None:
        """Seek to a specific ISO timestamp within the session window."""
        pass

    @abstractmethod
    async def set_speed(self, speed: float) -> None:
        """Set playback speed multiplier (e.g., 0.5x, 1.0x, 2.0x, 5.0x)."""
        pass

    @abstractmethod
    def get_playback_state(self) -> PlaybackState:
        """Get current playback and mode state."""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up background tasks, HTTP connections, or memory caches."""
        pass
