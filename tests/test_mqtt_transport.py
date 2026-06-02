"""Tests for the Neo MQTT push transport."""

from __future__ import annotations

import asyncio
import contextlib
import json
import ssl
from typing import Self
from unittest.mock import AsyncMock, patch

import pytest
from aiomqtt import MqttError

from custom_components.actronair_neo.api.push import create_push_transport
from custom_components.actronair_neo.api.push.models import (
    PushState,
    RealtimeConnectionDetails,
)
from custom_components.actronair_neo.api.push.mqtt_transport import MqttPushTransport

DETAILS = RealtimeConnectionDetails(
    endpoint="mqtt.example", port=8883, protocol="ssl", user_id="u1"
)


def _transport(sink) -> MqttPushTransport:
    return MqttPushTransport(
        details=DETAILS,
        serial="SER1",
        token_provider=AsyncMock(return_value="tok"),
        on_update=sink,
    )


@pytest.mark.asyncio
async def test_dispatch_full_status_calls_sink_full():
    sink = AsyncMock()
    t = _transport(sink)
    await t._dispatch(
        "actron-cloud/u1/neo/ser1/mwc/full-status", json.dumps({"a": 1}).encode()
    )
    sink.assert_awaited_once_with({"a": 1}, "full")


@pytest.mark.asyncio
async def test_dispatch_status_change_calls_sink_delta():
    sink = AsyncMock()
    t = _transport(sink)
    await t._dispatch("x/mwc/status-change", json.dumps({"a": 2}).encode())
    sink.assert_awaited_once_with({"a": 2}, "delta")


@pytest.mark.asyncio
async def test_dispatch_heartbeat_updates_state_no_sink():
    sink = AsyncMock()
    t = _transport(sink)
    await t._dispatch("x/mwc/heart-beat", b"{}")
    sink.assert_not_awaited()
    assert t.state is PushState.CONNECTED
    assert t.last_heartbeat is not None


@pytest.mark.asyncio
async def test_dispatch_drops_bad_json():
    sink = AsyncMock()
    t = _transport(sink)
    await t._dispatch("x/mwc/full-status", b"\xff\xfe not json")
    sink.assert_not_awaited()


@pytest.mark.asyncio
async def test_dispatch_swallows_sink_error():
    sink = AsyncMock(side_effect=RuntimeError("boom"))
    t = _transport(sink)
    await t._dispatch("x/mwc/full-status", b"{}")  # must not raise


def test_topics_built_correctly():
    t = _transport(AsyncMock())
    assert t._topics == [
        "actron-cloud/u1/neo/SER1/mwc/full-status",
        "actron-cloud/u1/neo/SER1/mwc/status-change",
        "actron-cloud/u1/neo/SER1/mwc/heart-beat",
        "actron-cloud/u1/neo/SER1/mwc/cmd-response/+/+",
    ]


@pytest.mark.asyncio
async def test_dispatch_cmd_response_ack_applies_event():
    """An ack'd command response forwards its embedded event as a delta."""
    sink = AsyncMock()
    t = _transport(sink)
    payload = {
        "correlationId": "m/cmd1",
        "commandResponse": {
            "type": "ack",
            "value": {"UserAirconSettings.QuietMode": False},
        },
        "event": {
            "type": "status-change-broadcast",
            "UserAirconSettings.QuietMode": False,
        },
        "wcFirmware": "2.6.2.3",
    }
    await t._dispatch(
        "actron-cloud/u1/neo/SER1/mwc/cmd-response/m/cmd1", json.dumps(payload).encode()
    )
    sink.assert_awaited_once_with(payload, "delta")


@pytest.mark.asyncio
async def test_dispatch_cmd_response_nack_warns(caplog):
    """A non-ack command response logs a warning."""
    sink = AsyncMock()
    t = _transport(sink)
    payload = {"commandResponse": {"type": "error", "value": {"x": 1}}}
    with caplog.at_level("WARNING"):
        await t._dispatch(
            "actron-cloud/u1/neo/SER1/mwc/cmd-response/m/cmd2",
            json.dumps(payload).encode(),
        )
    assert "not acknowledged" in caplog.text
    # No embedded event → nothing forwarded to the sink.
    sink.assert_not_awaited()


@pytest.mark.asyncio
async def test_dispatch_cmd_response_without_event_not_forwarded():
    """An ack with no embedded event is logged but not forwarded."""
    sink = AsyncMock()
    t = _transport(sink)
    payload = {"commandResponse": {"type": "ack", "value": {}}}
    await t._dispatch(
        "actron-cloud/u1/neo/SER1/mwc/cmd-response/m/cmd3", json.dumps(payload).encode()
    )
    sink.assert_not_awaited()


def test_backoff_schedule():
    t = _transport(AsyncMock())
    delays = []
    d = t._reconnect_initial
    for _ in range(9):
        delays.append(d)
        d = min(d * 2, t._reconnect_max)
    assert delays == [0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 60.0, 60.0]


@pytest.mark.asyncio
async def test_token_fetched_each_connect():
    provider = AsyncMock(return_value="tok")
    t = MqttPushTransport(
        details=DETAILS, serial="SER1", token_provider=provider, on_update=AsyncMock()
    )
    token = await t._token_provider()
    assert token == "tok"
    provider.assert_awaited()


def test_factory_neo_returns_mqtt():
    t = create_push_transport(
        platform="neo",
        details=DETAILS,
        serial="SER1",
        token_provider=AsyncMock(),
        on_update=AsyncMock(),
    )
    assert isinstance(t, MqttPushTransport)


def test_factory_passes_ssl_context_to_transport():
    sentinel = ssl.create_default_context()
    t = create_push_transport(
        platform="neo",
        details=DETAILS,
        serial="SER1",
        token_provider=AsyncMock(),
        on_update=AsyncMock(),
        ssl_context=sentinel,
    )
    assert isinstance(t, MqttPushTransport)
    assert t._ssl_context is sentinel


def test_default_client_factory_uses_injected_ssl_context():
    sentinel = ssl.create_default_context()
    t = MqttPushTransport(
        details=DETAILS,
        serial="SER1",
        token_provider=AsyncMock(return_value="tok"),
        on_update=AsyncMock(),
        ssl_context=sentinel,
    )
    # The aiomqtt client must be built with our injected TLS context, not a
    # freshly created one (which would do blocking I/O and use the OS trust store).
    with patch(
        "custom_components.actronair_neo.api.push.mqtt_transport.Client"
    ) as mock_client:
        t._default_client_factory("tok")
    assert mock_client.call_args.kwargs["tls_context"] is sentinel


def test_factory_que_returns_none():
    assert (
        create_push_transport(
            platform="que",
            details=DETAILS,
            serial="SER1",
            token_provider=AsyncMock(),
            on_update=AsyncMock(),
        )
        is None
    )


# ---------------------------------------------------------------------------
# Fake helpers for start() integration tests
# ---------------------------------------------------------------------------


class _FakeMessage:
    """Minimal stand-in for an aiomqtt message."""

    def __init__(self, topic: str, payload: bytes) -> None:
        self.topic = topic
        self.payload = payload


class _FakeClient:
    """Async-context client that yields messages then blocks (live connection)."""

    def __init__(self, messages: list[_FakeMessage]) -> None:
        self._messages = messages
        self.subscribed: list[str] = []
        self.enter_count = 0

    async def __aenter__(self) -> Self:
        self.enter_count += 1
        return self

    async def __aexit__(self, *_exc: object) -> bool:
        return False

    async def subscribe(self, topic: str) -> None:
        self.subscribed.append(topic)

    async def _gen(self):
        for message in self._messages:
            yield message
        # Emulate an open connection waiting for more messages.
        await asyncio.Event().wait()

    @property
    def messages(self):
        return self._gen()


class _FailingClient:
    """Client whose connect (aenter) raises, to exercise reconnect."""

    async def __aenter__(self) -> Self:
        raise MqttError("connect failed")

    async def __aexit__(self, *_exc: object) -> bool:
        return False


@pytest.mark.asyncio
async def test_start_fetches_token_subscribes_and_dispatches():
    sink = AsyncMock()
    provider = AsyncMock(return_value="tok")
    msg = _FakeMessage("actron-cloud/u1/neo/SER1/mwc/full-status", b'{"a": 1}')
    client = _FakeClient([msg])
    t = MqttPushTransport(
        details=DETAILS,
        serial="SER1",
        token_provider=provider,
        on_update=sink,
        client_factory=lambda _token: client,
    )
    task = asyncio.create_task(t.start())
    try:
        # Allow the loop to connect, subscribe, and dispatch the one message.
        for _ in range(20):
            await asyncio.sleep(0)
            if sink.await_count:
                break
        provider.assert_awaited()
        assert client.subscribed == t._topics
        sink.assert_awaited_once_with({"a": 1}, "full")
        assert t.state is PushState.CONNECTED
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


@pytest.mark.asyncio
async def test_start_reconnects_with_backoff_and_refetches_token(monkeypatch):
    sink = AsyncMock()
    provider = AsyncMock(return_value="tok")
    clients = [_FailingClient(), _FakeClient([])]
    t = MqttPushTransport(
        details=DETAILS,
        serial="SER1",
        token_provider=provider,
        on_update=sink,
        client_factory=lambda _token: clients.pop(0),
    )
    sleeps: list[float] = []
    _real_sleep = asyncio.sleep  # save before patching

    async def _fake_sleep(delay: float) -> None:
        sleeps.append(delay)
        await _real_sleep(0)  # yield to event loop without the real delay

    monkeypatch.setattr(
        "custom_components.actronair_neo.api.push.mqtt_transport.asyncio.sleep",
        _fake_sleep,
    )
    task = asyncio.create_task(t.start())
    try:
        for _ in range(200):
            await _real_sleep(0)
            if t.reconnect_count >= 1 and provider.await_count >= 2:
                break
        assert t.reconnect_count == 1
        assert sleeps  # backoff sleep was called
        assert sleeps[0] == 0.5  # first backoff is the initial 0.5s
        assert provider.await_count >= 2  # token refetched on the retry connect
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
