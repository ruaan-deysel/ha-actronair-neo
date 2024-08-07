"""The Actron Air Neo integration."""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.exceptions import ConfigEntryNotReady
from .const import (
    DOMAIN,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_REFRESH_INTERVAL,
    CONF_SERIAL_NUMBER,
    SERVICE_FORCE_UPDATE
)
from .coordinator import ActronDataCoordinator
from .api import ActronApi, AuthenticationError, ApiError

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["climate", "sensor", "switch"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Actron Air Neo from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    refresh_interval = entry.data[CONF_REFRESH_INTERVAL]
    serial_number = entry.data[CONF_SERIAL_NUMBER]

    session = async_get_clientsession(hass)
    api = ActronApi(username, password, session=session)

    try:
        await api.authenticate()
    except AuthenticationError as auth_err:
        _LOGGER.error("Failed to authenticate: %s", auth_err)
        raise ConfigEntryNotReady from auth_err
    except ApiError as api_err:
        _LOGGER.error("Failed to connect to Actron Air Neo API: %s", api_err)
        raise ConfigEntryNotReady from api_err

    coordinator = ActronDataCoordinator(hass, api, serial_number, refresh_interval)

    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady as err:
        _LOGGER.error("Failed to load initial data: %s", err)
        raise
    except Exception as err:
        _LOGGER.error("Unexpected error occurred: %s", err)
        raise ConfigEntryNotReady from err

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def force_update(call: ServiceCall) -> None:
        """Force an update of the data."""
        _LOGGER.debug("Forcing an update for Actron Air Neo")
        await coordinator.async_refresh()

    hass.services.async_register(DOMAIN, SERVICE_FORCE_UPDATE, force_update)

    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        hass.services.async_remove(DOMAIN, SERVICE_FORCE_UPDATE)
    return unload_ok

async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener."""
    await hass.config_entries.async_reload(entry.entry_id)