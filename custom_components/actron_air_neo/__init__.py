"""The Actron Air Neo integration."""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.exceptions import ConfigEntryNotReady
from .const import DOMAIN, CONF_USERNAME, CONF_PASSWORD, CONF_REFRESH_INTERVAL, CONF_SERIAL_NUMBER
from .const import ERROR_CANNOT_CONNECT, ERROR_UNKNOWN
from .coordinator import ActronDataCoordinator
from .api import ActronApi, AuthenticationError, ApiError

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["climate", "sensor"]

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
    except ConfigEntryNotReady:
        _LOGGER.error(ERROR_CANNOT_CONNECT)
        raise
    except Exception as err:
        _LOGGER.error("%s: %s", ERROR_UNKNOWN, err)
        raise ConfigEntryNotReady from err

    hass.data[DOMAIN][entry.entry_id] = coordinator

    async def force_update(call):
        """Handle the service call to force an update."""
        await coordinator.async_force_update()

    hass.services.async_register(DOMAIN, "force_update", force_update)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)