"""The ActronAir Neo integration."""
import asyncio
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.exceptions import ConfigEntryNotReady
from .const import (
    DOMAIN,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_REFRESH_INTERVAL,
    CONF_SERIAL_NUMBER,
    SERVICE_FORCE_UPDATE,
    PLATFORM_CLIMATE,
    PLATFORM_SENSOR,
    PLATFORM_SWITCH
)
from .coordinator import ActronDataCoordinator
from .api import ActronApi, AuthenticationError, ApiError

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = [PLATFORM_CLIMATE, PLATFORM_SENSOR, PLATFORM_SWITCH]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ActronAir Neo from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    refresh_interval = entry.data[CONF_REFRESH_INTERVAL]
    serial_number = entry.data[CONF_SERIAL_NUMBER]

    session = async_get_clientsession(hass)
    api = ActronApi(username, password, session, hass.config.path("actron_neo_tokens"))

    try:
        await api.initializer()
    except AuthenticationError as auth_err:
        _LOGGER.error("Failed to authenticate: %s", auth_err)
        raise ConfigEntryNotReady from auth_err
    except ApiError as api_err:
        _LOGGER.error("Failed to connect to ActronAir Neo API: %s", api_err)
        raise ConfigEntryNotReady from api_err

    coordinator = ActronDataCoordinator(hass, api, serial_number, refresh_interval)

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def force_update(call):
        """Force update of all entities."""
        await coordinator.async_request_refresh()

    hass.services.async_register(DOMAIN, SERVICE_FORCE_UPDATE, force_update)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    if not hass.data[DOMAIN]:
        hass.services.async_remove(DOMAIN, SERVICE_FORCE_UPDATE)

    return unload_ok

async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener."""
    await hass.config_entries.async_reload(entry.entry_id)

async def force_update(hass, call):
    """Force update of all entities."""
    for entry_id, coordinator in hass.data[DOMAIN].items():
        await coordinator.async_request_refresh()

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)