from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD, CONF_DEVICE_ID
from homeassistant.exceptions import ConfigEntryNotReady
from .const import DOMAIN, PLATFORMS, DEFAULT_UPDATE_INTERVAL
from .api import ActronApi
from .coordinator import async_setup_coordinator
import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Actron Air Neo component."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Actron Air Neo from a config entry."""
    try:
        api = ActronApi(
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD]
        )

        update_interval = entry.options.get("update_interval", DEFAULT_UPDATE_INTERVAL)
        coordinator = await async_setup_coordinator(
            hass,
            api,
            entry.data[CONF_DEVICE_ID],
            update_interval
        )

        hass.data[DOMAIN][entry.entry_id] = coordinator

        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        
        entry.async_on_unload(entry.add_update_listener(update_listener))
        return True
    except Exception as exc:
        _LOGGER.error("Error setting up Actron Air Neo integration: %s", exc)
        raise ConfigEntryNotReady from exc

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.api.close()
    return unload_ok

async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)