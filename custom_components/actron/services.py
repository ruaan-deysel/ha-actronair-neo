from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import device_registry as dr
from .const import DOMAIN

async def async_setup_services(hass: HomeAssistant):
    async def set_zone_state(call: ServiceCall):
        device_id = call.data["device_id"]
        zone_id = call.data["zone_id"]
        enabled = call.data["enabled"]
        
        device_registry = dr.async_get(hass)
        device_entry = device_registry.async_get(device_id)
        if device_entry is None:
            raise ValueError(f"Device {device_id} not found")
        
        coordinator = hass.data[DOMAIN][device_entry.config_entries[0]]
        await coordinator.api.send_command(coordinator.device_id, {
            f"UserAirconSettings.EnabledZones[{zone_id}]": enabled
        })
        await coordinator.async_request_refresh()

    async def set_away_mode(call: ServiceCall):
        device_id = call.data["device_id"]
        away_mode = call.data["away_mode"]
        
        device_registry = dr.async_get(hass)
        device_entry = device_registry.async_get(device_id)
        if device_entry is None:
            raise ValueError(f"Device {device_id} not found")
        
        coordinator = hass.data[DOMAIN][device_entry.config_entries[0]]
        await coordinator.api.send_command(coordinator.device_id, {
            "UserAirconSettings.AwayMode": away_mode
        })
        await coordinator.async_request_refresh()

    hass.services.async_register(DOMAIN, "set_zone_state", set_zone_state)
    hass.services.async_register(DOMAIN, "set_away_mode", set_away_mode)

async def async_unload_services(hass: HomeAssistant):
    hass.services.async_remove(DOMAIN, "set_zone_state")
    hass.services.async_remove(DOMAIN, "set_away_mode")