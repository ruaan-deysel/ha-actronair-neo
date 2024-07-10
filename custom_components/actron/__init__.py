from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN

async def async_setup(hass: HomeAssistant, config: dict):
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.async_add_job(hass.config_entries.async_forward_entry_setup(entry, "climate"))
    hass.async_add_job(hass.config_entries.async_forward_entry_setup(entry, "sensor"))
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_forward_entry_unload(entry, "climate")
    await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    return True
