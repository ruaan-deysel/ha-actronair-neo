"""Tests for the SSL context helpers."""

import ssl

import pytest
from homeassistant.core import HomeAssistant

from custom_components.actronair_neo.ssl_helper import (
    _MQTT_INTERMEDIATE_CERT,
    _build_mqtt_ssl_context,
    async_get_mqtt_ssl_context,
)


def test_bundled_intermediate_cert_exists():
    """The Sectigo intermediate must be packaged with the integration."""
    assert _MQTT_INTERMEDIATE_CERT.is_file()


def test_mqtt_ssl_context_keeps_chain_verification_off_hostname():
    """MQTT context disables hostname check but keeps chain verification."""
    ctx = _build_mqtt_ssl_context()
    assert ctx.check_hostname is False
    assert ctx.verify_mode is ssl.CERT_REQUIRED


def test_mqtt_ssl_context_loads_intermediate():
    """Building the context loads the bundled intermediate without error."""
    ctx = _build_mqtt_ssl_context()
    subjects = {
        dict(c).get("subject")
        for c in ctx.get_ca_certs()  # type: ignore[arg-type]
    }
    # The bundled intermediate's CN should be present among loaded CAs.
    flat = str(subjects)
    assert "Sectigo Public Server Authentication CA DV R36" in flat


@pytest.mark.asyncio
async def test_async_get_mqtt_ssl_context_is_cached(hass: HomeAssistant):
    """The context is built once and reused from hass.data."""
    first = await async_get_mqtt_ssl_context(hass)
    second = await async_get_mqtt_ssl_context(hass)
    assert first is second
