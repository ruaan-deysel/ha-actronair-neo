"""Abstract contract shared by realtime push transports."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from .models import PushState

if TYPE_CHECKING:
    from datetime import datetime

# A sink that receives parsed JSON payloads: (payload, kind) where kind is
# "full" (authoritative snapshot) or "delta" (partial status-change).
UpdateSink = Callable[[dict[str, Any], str], Awaitable[None]]
# Returns a fresh, valid OAuth access token for use as the MQTT password.
TokenProvider = Callable[[], Awaitable[str]]


class PushTransport(ABC):
    """Base class for realtime push transports."""

    def __init__(self) -> None:
        """Initialise common transport state."""
        self._state: PushState = PushState.DISCONNECTED
        self._last_heartbeat: datetime | None = None
        self._reconnect_count: int = 0
        self._last_error: str | None = None

    @abstractmethod
    async def start(self) -> None:
        """Run the connect/listen loop until ``stop`` is called."""

    @abstractmethod
    async def stop(self) -> None:
        """Signal the loop to exit and disconnect cleanly."""

    @property
    def state(self) -> PushState:
        """Return the current connection state."""
        return self._state

    @property
    def last_heartbeat(self) -> datetime | None:
        """Return the timestamp of the last heartbeat message, if any."""
        return self._last_heartbeat

    @property
    def reconnect_count(self) -> int:
        """Return the number of reconnect attempts so far."""
        return self._reconnect_count

    @property
    def last_error(self) -> str | None:
        """Return the class name of the last connection error, if any."""
        return self._last_error
