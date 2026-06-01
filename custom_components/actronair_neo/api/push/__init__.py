"""Realtime push transport for the ActronAir Neo integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base import PushTransport

if TYPE_CHECKING:
    from .base import TokenProvider, UpdateSink
    from .models import RealtimeConnectionDetails

_LOGGER = logging.getLogger(__name__)

__all__ = ["PushTransport", "create_push_transport"]


def create_push_transport(
    *,
    platform: str,
    details: RealtimeConnectionDetails,
    serial: str,
    token_provider: TokenProvider,
    on_update: UpdateSink,
) -> PushTransport | None:
    """Return a push transport for the platform, or None if unsupported."""
    if platform == "neo":
        # Imported lazily so the aiomqtt dependency is only required when used.
        from .mqtt_transport import MqttPushTransport  # noqa: PLC0415

        return MqttPushTransport(
            details=details,
            serial=serial,
            token_provider=token_provider,
            on_update=on_update,
        )
    _LOGGER.info(
        "Realtime push not yet implemented for platform %r; polling only", platform
    )
    return None
