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
    MQTT_TOPIC_CMD_RESPONSE,
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

    def __init__(  # noqa: PLR0913
        self,
        *,
        details: RealtimeConnectionDetails,
        serial: str,
        token_provider: TokenProvider,
        on_update: UpdateSink,
        ssl_context: ssl.SSLContext | None = None,
        client_factory: Callable[[str], Client] | None = None,
    ) -> None:
        """Initialise the transport (no connection is opened here)."""
        super().__init__()
        self._details = details
        self._token_provider = token_provider
        self._on_update = on_update
        # A certifi-backed SSL context built off the event loop by the caller.
        # Building it here would do blocking file I/O inside the loop and fall
        # back to the OS trust store, which fails to verify the broker cert
        # (see issue #96 / ssl_helper).
        self._ssl_context = ssl_context
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
            # Two trailing wildcards: .../cmd-response/{machine}/{commandId}.
            f"{base}/{MQTT_TOPIC_CMD_RESPONSE}/+/+",
        ]

    def _default_client_factory(self, token: str) -> Client:
        """Build an aiomqtt client for the discovered broker."""
        kwargs: dict[str, Any] = {
            "username": "",
            "password": token,
            "keepalive": MQTT_KEEPALIVE,
            "identifier": uuid.uuid4().hex,
            # A fresh random identifier is used on every (re)connect and topics
            # are re-subscribed each time, so there is no session to resume.
            # Use a clean session to avoid leaving orphaned persistent sessions
            # on the broker after each reconnect.
            "clean_session": True,
        }
        if self._details.uses_tls:
            # Prefer the injected certifi-backed context; only fall back to a
            # default context if none was provided (e.g. direct instantiation
            # in tests, which never open a real connection).
            kwargs["tls_context"] = self._ssl_context or ssl.create_default_context()
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
        elif MQTT_TOPIC_CMD_RESPONSE in topic:
            # A command response acks/nacks a command and also embeds a
            # status-change event. Surface a non-ack as a warning, then apply
            # the embedded event (if any) for instant command confirmation.
            self._log_command_response(data)
            if not isinstance(data.get("event"), dict):
                return
            kind = "delta"
        else:
            return
        try:
            await self._on_update(data, kind)
        except Exception:
            _LOGGER.exception("Push update sink raised; ignoring message")

    @staticmethod
    def _log_command_response(data: dict[str, Any]) -> None:
        """Log a command acknowledgement, warning on any non-ack response."""
        raw_response = data.get("commandResponse")
        if not isinstance(raw_response, dict):
            return
        response = cast("dict[str, Any]", raw_response)
        response_type = response.get("type")
        if response_type and response_type != "ack":
            _LOGGER.warning(
                "ActronAir command was not acknowledged (type=%s): %s",
                response_type,
                response.get("value"),
            )
        else:
            _LOGGER.debug("ActronAir command acknowledged: %s", response.get("value"))

    async def start(self) -> None:
        """Run the connect/listen loop with exponential reconnect backoff."""
        self._running = True
        delay = self._reconnect_initial
        _LOGGER.debug(
            "Starting MQTT push to %s:%s (tls=%s)",
            self._details.endpoint,
            self._details.port,
            self._details.uses_tls,
        )
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
