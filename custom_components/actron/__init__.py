from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD, CONF_DEVICE_ID
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_import_module
from .const import DOMAIN, PLATFORMS, DEFAULT_UPDATE_INTERVAL
import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Actron Air Neo component."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Actron Air Neo from a config entry."""
    try:
        api_module = await async_import_module(hass, f"{DOMAIN}.api")
        coordinator_module = await async_import_module(hass, f"{DOMAIN}.coordinator")
        services_module = await async_import_module(hass, f"{DOMAIN}.services")

        api = api_module.ActronApi(
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD]
        )

        update_interval = entry.options.get("update_interval", DEFAULT_UPDATE_INTERVAL)
        coordinator = coordinator_module.ActronDataCoordinator(
            hass,
            api,
            entry.data[CONF_DEVICE_ID],
            update_interval
        )

        await coordinator.async_config_entry_first_refresh()

        hass.data[DOMAIN][entry.entry_id] = coordinator

        for platform in PLATFORMS:
            hass.async_create_task(
                hass.config_entries.async_forward_entry_setup(entry, platform)
            )

        await services_module.async_setup_services(hass)
        
        entry.async_on_unload(entry.add_update_listener(update_listener))
        return True
    except Exception as exc:
        _LOGGER.error("Error setting up Actron Air Neo integration: %s", exc)
        raise ConfigEntryNotReady from exc

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.api.close()
        services_module = await async_import_module(hass, f"{DOMAIN}.services")
        await services_module.async_unload_services(hass)
    return unload_ok

async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)