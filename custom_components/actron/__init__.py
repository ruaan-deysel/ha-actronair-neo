"""Actron Air Neo integration for Home Assistant."""

import logging
from homeassistant.helpers.discovery import load_platform
from .api import ActronNeoAPI
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry):
    """Set up Actron Neo from a config entry."""
    api = ActronNeoAPI(
        username=config_entry.data["username"],
        password=config_entry.data["password"]
    )
    
    zones = config_entry.data.get("zones", [])
    
    hass.data[DOMAIN] = {
        "api": api,
        "zones": [{"id": zone["id"], "name": zone["name"]} for zone in zones]
    }
    
    # Discover climate platform
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(config_entry, "climate")
    )
    
    return True

async def async_unload_entry(hass, config_entry):
    """Unload a config entry."""
    await hass.config_entries.async_forward_entry_unload(config_entry, "climate")
    
    # Close the aiohttp session
    api = hass.data[DOMAIN]["api"]
    await api.close_session()
    
    hass.data.pop(DOMAIN)
    return True
