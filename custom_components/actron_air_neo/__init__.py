import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.exceptions import ConfigEntryNotReady
from .const import DOMAIN, CONF_USERNAME, CONF_PASSWORD, CONF_REFRESH_INTERVAL, CONF_SERIAL_NUMBER
from .coordinator import ActronDataCoordinator
from .api import ActronApi

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    refresh_interval = entry.data[CONF_REFRESH_INTERVAL]
    serial_number = entry.data[CONF_SERIAL_NUMBER]

    session = async_get_clientsession(hass)
    api = ActronApi(username, password, session=session)

    try:
        await api.authenticate()
    except Exception as err:
        _LOGGER.error("Failed to authenticate: %s", err)
        raise ConfigEntryNotReady from err

    coordinator = ActronDataCoordinator(hass, api, serial_number, refresh_interval)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, ["climate", "sensor"])

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["climate", "sensor"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok