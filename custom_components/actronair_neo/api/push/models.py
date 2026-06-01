"""Models for the realtime push transport."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, cast


class PushState(StrEnum):
    """Lifecycle state of a push transport."""

    DISABLED = "disabled"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    STALE = "stale"


_TLS_PROTOCOLS = frozenset({"ssl", "tls", "mqtts"})


def _first(data: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    """Return the first present, truthy string value among ``keys``."""
    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value:
            return value
    return None


@dataclass(frozen=True)
class RealtimeConnectionDetails:
    """Broker connection details returned by the discovery endpoint."""

    endpoint: str
    port: int
    protocol: str
    user_id: str

    @property
    def uses_tls(self) -> bool:
        """Return True when the broker connection should use TLS."""
        return self.protocol.lower() in _TLS_PROTOCOLS

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> RealtimeConnectionDetails | None:
        """Parse a discovery payload, tolerating field-name variations."""
        details = payload.get("RTCDetails") or payload.get("rtcDetails") or payload
        if not isinstance(details, dict):
            return None
        details = cast("dict[str, Any]", details)
        endpoint = _first(
            details, ("endPoint", "endpoint", "Endpoint", "host", "server")
        )
        if not endpoint:
            return None
        user_id = (
            _first(details, ("userId", "UserId", "user_id", "username")) or "unknown"
        )
        protocol = _first(details, ("protocol", "Protocol", "scheme")) or "ssl"
        port_raw = details.get("port", details.get("Port"))
        if isinstance(port_raw, bool):
            port = 443
        elif isinstance(port_raw, int):
            port = port_raw
        elif isinstance(port_raw, str) and port_raw.isdigit():
            port = int(port_raw)
        else:
            port = 443
        return cls(endpoint=endpoint, port=port, protocol=protocol, user_id=user_id)
