"""Neo realtime push transport over MQTT (aiomqtt)."""

from __future__ import annotations

import asyncio
import json
import logging
import ssl
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, cast

from aiomqtt import Client, MqttError

from custom_components.actronair_neo.api.const import (
    MQTT_KEEPALIVE,
    MQTT_PLATFORM_NEO,
    MQTT_RECONNECT_INITIAL,
    MQTT_RECONNECT_MAX,
    MQTT_TOPIC_FULL_STATUS,
    MQTT_TOPIC_HEART_BEAT,
    MQTT_TOPIC_PREFIX,
    MQTT_TOPIC_STATUS_CHANGE,
)

from .base import PushTransport
from .models import PushState

if TYPE_CHECKING:
    from collections.abc import Callable

    from .base import TokenProvider, UpdateSink
    from .models import RealtimeConnectionDetails

_LOGGER = logging.getLogger(__name__)


class MqttPushTransport(PushTransport):
    """Subscribe to Neo MQTT topics and forward status updates to a sink."""

    def __init__(
        self,
        *,
        details: RealtimeConnectionDetails,
        serial: str,
        token_provider: TokenProvider,
        on_update: UpdateSink,
        client_factory: Callable[[str], Client] | None = None,
    ) -> None:
        """Initialise the transport (no connection is opened here)."""
        super().__init__()
        self._details = details
        self._token_provider = token_provider
        self._on_update = on_update
        self._client_factory: Callable[[str], Client] = (
            client_factory
            if client_factory is not None
            else self._default_client_factory
        )
        self._running = False
        self._reconnect_initial: float = MQTT_RECONNECT_INITIAL
        self._reconnect_max: float = MQTT_RECONNECT_MAX
        base = f"{MQTT_TOPIC_PREFIX}/{details.user_id}/{MQTT_PLATFORM_NEO}/{serial}"
        self._topics = [
            f"{base}/{MQTT_TOPIC_FULL_STATUS}",
            f"{base}/{MQTT_TOPIC_STATUS_CHANGE}",
            f"{base}/{MQTT_TOPIC_HEART_BEAT}",
        ]

    def _default_client_factory(self, token: str) -> Client:
        """Build an aiomqtt client for the discovered broker."""
        kwargs: dict[str, Any] = {
            "username": "",
            "password": token,
            "keepalive": MQTT_KEEPALIVE,
            "identifier": uuid.uuid4().hex,
            "clean_session": False,
        }
        if self._details.uses_tls:
            kwargs["tls_context"] = ssl.create_default_context()
        return Client(self._details.endpoint, self._details.port, **kwargs)

    async def _dispatch(self, topic: str, payload: bytes) -> None:
        """Route one incoming MQTT message to the sink or heartbeat tracker."""
        if topic.endswith(MQTT_TOPIC_HEART_BEAT):
            self._last_heartbeat = datetime.now()  # noqa: DTZ005
            self._state = PushState.CONNECTED
            return
        try:
            data = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            _LOGGER.debug("Dropping undecodable push message on %s", topic)
            return
        if not isinstance(data, dict):
            return
        data = cast("dict[str, Any]", data)
        if topic.endswith(MQTT_TOPIC_FULL_STATUS):
            kind = "full"
        elif topic.endswith(MQTT_TOPIC_STATUS_CHANGE):
            kind = "delta"
        else:
            return
        try:
            await self._on_update(data, kind)
        except Exception:
            _LOGGER.exception("Push update sink raised; ignoring message")

    async def start(self) -> None:
        """Run the connect/listen loop with exponential reconnect backoff."""
        self._running = True
        delay = self._reconnect_initial
        while self._running:
            try:
                self._state = PushState.CONNECTING
                token = await self._token_provider()
                async with self._client_factory(token) as client:
                    self._state = PushState.CONNECTED
                    self._last_error = None
                    delay = self._reconnect_initial
                    for topic in self._topics:
                        await client.subscribe(topic)
                    async for message in client.messages:
                        await self._dispatch(str(message.topic), message.payload)  # type: ignore[arg-type]
            except asyncio.CancelledError:
                raise
            except (MqttError, OSError) as err:
                if not self._running:
                    break
                self._reconnect_count += 1
                self._last_error = type(err).__name__
                self._state = PushState.DISCONNECTED
                _LOGGER.debug(
                    "Push disconnected (%s); reconnecting in %.1fs", err, delay
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, self._reconnect_max)
        self._state = PushState.DISCONNECTED

    async def stop(self) -> None:
        """Signal the loop to exit; the client context closes the connection."""
        self._running = False
        self._state = PushState.DISCONNECTED
