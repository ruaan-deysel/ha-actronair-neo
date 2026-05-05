"""
SSL context helper for ActronAir Neo API connections.

Home Assistant 2026.4 switched the default SSL trust store from Python's
``certifi`` bundle to ``truststore`` (using the OS-level CA store). The
container image (Alpine Linux based) does not include the DigiCert High
Assurance EV Root CA used by ``nimbus.actronair.com.au``, which causes::

    SSLCertVerificationError: certificate verify failed:
        unable to get local issuer certificate

To work around this, the integration uses its own SSL context backed by
the ``certifi`` CA bundle (always available in HA's runtime), plus a
private ``aiohttp.ClientSession`` configured to use it.

See: https://github.com/ruaan-deysel/ha-actronair-neo/issues/96
"""

from __future__ import annotations

import ssl
from typing import TYPE_CHECKING

import aiohttp  # type: ignore[import-untyped]
import certifi  # type: ignore[import-untyped]

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant  # type: ignore[import-untyped]

_SSL_CONTEXT_KEY = f"{DOMAIN}_ssl_context"


def _build_ssl_context() -> ssl.SSLContext:
    """
    Build an SSL context using certifi's CA bundle.

    Loading the CA bundle hits the filesystem, so this must be called from
    an executor thread, not the event loop.
    """
    return ssl.create_default_context(cafile=certifi.where())


async def async_get_ssl_context(hass: HomeAssistant) -> ssl.SSLContext:
    """
    Return a shared certifi-backed SSL context.

    The context is built once per Home Assistant instance and cached in
    ``hass.data``.
    """
    ctx = hass.data.get(_SSL_CONTEXT_KEY)
    if ctx is None:
        ctx = await hass.async_add_executor_job(_build_ssl_context)
        hass.data[_SSL_CONTEXT_KEY] = ctx
    return ctx


async def async_create_clientsession(hass: HomeAssistant) -> aiohttp.ClientSession:
    """
    Create an aiohttp ClientSession that trusts the certifi CA bundle.

    The caller is responsible for closing the returned session.
    """
    ctx = await async_get_ssl_context(hass)
    connector = aiohttp.TCPConnector(ssl=ctx)
    return aiohttp.ClientSession(connector=connector)
