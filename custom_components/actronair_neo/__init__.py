"""The ActronAir Neo integration."""
import logging
from homeassistant.config_entries import ConfigEntry # type: ignore
from homeassistant.core import HomeAssistant, ServiceCall # type: ignore
from homeassistant.helpers import service # type: ignore
from homeassistant.helpers.aiohttp_client import async_get_clientsession # type: ignore
from homeassistant.exceptions import ConfigEntryNotReady # type: ignore
from homeassistant.helpers import entity_registry as er # type: ignore
from .const import (
    DOMAIN,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_REFRESH_INTERVAL,
    CONF_SERIAL_NUMBER,
    CONF_ENABLE_ZONE_CONTROL,
    SERVICE_FORCE_UPDATE,
    PLATFORM_CLIMATE,
    PLATFORM_SENSOR,
    PLATFORM_SWITCH,
    PLATFORM_BINARY_SENSOR
)
from .coordinator import ActronDataCoordinator
from .api import ActronApi, AuthenticationError, ApiError

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = [
    PLATFORM_CLIMATE,
    PLATFORM_SENSOR,
    PLATFORM_SWITCH,
    PLATFORM_BINARY_SENSOR
]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ActronAir Neo from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    refresh_interval = entry.data[CONF_REFRESH_INTERVAL]
    serial_number = entry.data[CONF_SERIAL_NUMBER]

    session = async_get_clientsession(hass)
    api = ActronApi(username, password, session, hass.config.path())

    try:
        await api.initializer()
    except AuthenticationError as auth_err:
        _LOGGER.error("Failed to authenticate: %s", auth_err)
        raise ConfigEntryNotReady from auth_err
    except ApiError as api_err:
        _LOGGER.error("Failed to connect to ActronAir Neo API: %s", api_err)
        raise ConfigEntryNotReady from api_err

    enable_zone_control = entry.options.get(CONF_ENABLE_ZONE_CONTROL, False)
    coordinator = ActronDataCoordinator(hass, api, serial_number, refresh_interval, enable_zone_control)

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(update_listener))

    async def force_update(call: ServiceCall) -> None:
        """Force update of all entities."""
        target_entities = await service.async_extract_entities(hass, call)
        for entity in target_entities:
            if entity.domain == PLATFORM_CLIMATE:
                coordinator = hass.data[DOMAIN][entity.platform.config_entry.entry_id]
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
    """Handle configuration entry updates with safe entity cleanup.
    
    This method ensures proper cleanup of entities when disabling zone control
    and maintains system stability during configuration changes.
    """
    coordinator = hass.data[DOMAIN][entry.entry_id]
    old_enable_zone_control = coordinator.enable_zone_control
    new_enable_zone_control = entry.options[CONF_ENABLE_ZONE_CONTROL]

    try:
        if old_enable_zone_control and not new_enable_zone_control:
            _LOGGER.debug("Zone control being disabled, cleaning up entities")
            entity_registry = er.async_get(hass)
            entries = er.async_entries_for_config_entry(entity_registry, entry.entry_id)
            
            # First, remove entities from registry
            for entity_entry in entries:
                if entity_entry.unique_id.startswith(f"{coordinator.device_id}_zone_"):
                    _LOGGER.debug(f"Removing entity: {entity_entry.entity_id}")
                    entity_registry.async_remove(entity_entry.entity_id)
            
            # Then update coordinator state
            await coordinator.set_enable_zone_control(new_enable_zone_control)
            
            # Finally, request a state refresh
            await coordinator.async_request_refresh()
        
        # Reload the config entry to apply changes
        await hass.config_entries.async_reload(entry.entry_id)
        _LOGGER.info(f"Successfully updated zone control setting to: {new_enable_zone_control}")
        
    except Exception as err:
        _LOGGER.error(f"Error updating zone control setting: {err}")
        raise

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)