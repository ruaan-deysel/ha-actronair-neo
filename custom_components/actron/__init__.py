"""Actron Neo integration for Home Assistant."""

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from .api import ActronNeoAPI
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Actron Neo integration."""
    _LOGGER.info("Setting up Actron Neo integration")
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Actron Neo from a config entry."""
    _LOGGER.info("Setting up Actron Neo entry")

    try:
        api = ActronNeoAPI(
            username=config_entry.data["username"],
            password=config_entry.data["password"]
        )

        await api.login()
        
        hass.data[DOMAIN][config_entry.entry_id] = {
            "api": api,
            "zones": api._zones
        }
        
        # Forward entry setup to the desired platforms
        await hass.config_entries.async_forward_entry_setups(config_entry, ["climate", "switch", "sensor"])
        _LOGGER.info("Actron Neo platforms loaded successfully")
        
    except Exception as e:
        _LOGGER.error(f"Error setting up Actron Neo entry: {e}")
        return False

    return True

async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Actron Neo entry")
    
    unload_ok = await hass.config_entries.async_forward_entry_unload(config_entry, "climate")
    unload_ok = unload_ok and await hass.config_entries.async_forward_entry_unload(config_entry, "switch")
    unload_ok = unload_ok and await hass.config_entries.async_forward_entry_unload(config_entry, "sensor")
    
    if unload_ok:
        # Close the aiohttp session
        api = hass.data[DOMAIN][config_entry.entry_id]["api"]
        await api.close_session()
        
        hass.data[DOMAIN].pop(config_entry.entry_id)
        _LOGGER.info("Actron Neo entry unloaded successfully")
    
    else:
        _LOGGER.error("Error unloading Actron Neo entry")
    
    return unload_ok
