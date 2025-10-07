"""The ActronAir Neo integration."""

import logging
from homeassistant.config_entries import ConfigEntry  # type: ignore
from homeassistant.core import HomeAssistant, ServiceCall  # type: ignore
from homeassistant.helpers import service  # type: ignore
from homeassistant.helpers.aiohttp_client import async_get_clientsession  # type: ignore
from homeassistant.exceptions import ConfigEntryNotReady  # type: ignore
from homeassistant.helpers import entity_registry as er  # type: ignore
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
    PLATFORM_BINARY_SENSOR,
)
from .coordinator import ActronDataCoordinator
from .api import ActronApi, AuthenticationError, ApiError, ConfigurationError, ZoneError
from . import repairs

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = [
    PLATFORM_CLIMATE,
    PLATFORM_SENSOR,
    PLATFORM_SWITCH,
    PLATFORM_BINARY_SENSOR,
]


async def async_migrate_entities(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> None:
    """Migrate old entity IDs to new entity IDs."""
    entity_registry = er.async_get(hass)
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    entity_entries = er.async_entries_for_config_entry(
        entity_registry, config_entry.entry_id
    )

    # Migration mappings
    migration_mappings = {
        f"{coordinator.device_id}_climate": f"{coordinator.device_id}_climate",
        f"{coordinator.device_id}_main_temperature": (
            f"{coordinator.device_id}_sensor_indoor_temperature"
        ),
        f"{coordinator.device_id}_filter_status": (
            f"{coordinator.device_id}_binary_sensor_filter_status"
        ),
        f"{coordinator.device_id}_system_status": (
            f"{coordinator.device_id}_binary_sensor_system_status"
        ),
        f"{coordinator.device_id}_system_health": (
            f"{coordinator.device_id}_binary_sensor_system_health"
        ),
        f"{coordinator.device_id}_away_mode": (
            f"{coordinator.device_id}_switch_away_mode"
        ),
        f"{coordinator.device_id}_quiet_mode": (
            f"{coordinator.device_id}_switch_quiet_mode"
        ),
        f"{coordinator.device_id}_continuous_fan": (
            f"{coordinator.device_id}_switch_continuous_fan"
        ),
    }

    # Add zone entity mappings
    for zone_id, zone_data in coordinator.data["zones"].items():
        zone_name = zone_data["name"].lower().replace(" ", "_")
        # Climate entities
        migration_mappings[f"{coordinator.device_id}_zone_{zone_id}"] = (
            f"{coordinator.device_id}_climate_zone_{zone_name}"
        )
        # Sensor entities
        migration_mappings[f"{coordinator.device_id}_zone_{zone_id}_temperature"] = (
            f"{coordinator.device_id}_sensor_zone_{zone_name}"
        )

    # Perform migration
    for entry in entity_entries:
        old_unique_id = entry.unique_id
        if old_unique_id in migration_mappings:
            new_unique_id = migration_mappings[old_unique_id]
            if old_unique_id != new_unique_id:
                _LOGGER.debug(
                    "Migrating entity %s from %s to %s",
                    entry.entity_id,
                    old_unique_id,
                    new_unique_id,
                )
                try:
                    entity_registry.async_update_entity(
                        entry.entity_id,
                        new_unique_id=new_unique_id,
                    )
                except er.HomeAssistantError as ex:
                    _LOGGER.error(
                        "Error migrating entity %s: %s", entry.entity_id, str(ex)
                    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ActronAir Neo from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Initialize API
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    refresh_interval = entry.data[CONF_REFRESH_INTERVAL]
    serial_number = entry.data[CONF_SERIAL_NUMBER]
    system_id = entry.data.get("system_id", "")

    session = async_get_clientsession(hass)
    api = ActronApi(username=username, password=password, session=session)

    try:
        await api.initializer()
        await api.set_system(serial_number, system_id)
    except AuthenticationError as auth_err:
        _LOGGER.error("Failed to authenticate: %s", auth_err)
        raise ConfigEntryNotReady from auth_err
    except ApiError as api_err:
        _LOGGER.error("Failed to connect to ActronAir Neo API: %s", api_err)
        raise ConfigEntryNotReady from api_err

    enable_zone_control = entry.options.get(CONF_ENABLE_ZONE_CONTROL, False)
    coordinator = ActronDataCoordinator(
        hass,
        api,
        serial_number,
        refresh_interval,
        enable_zone_control,
    )

    await coordinator.async_config_entry_first_refresh()
    await coordinator.async_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Perform migration before setting up platforms
    try:
        await async_migrate_entities(hass, entry)
    except er.HomeAssistantError as ex:
        _LOGGER.error("HomeAssistant error during entity migration: %s", str(ex))
        # Continue with setup even if migration fails
    except KeyError as ex:
        _LOGGER.error("Key error during entity migration: %s", str(ex))
        # Continue with setup even if migration fails
    except TypeError as ex:
        _LOGGER.error("Type error during entity migration: %s", str(ex))
        # Continue with setup even if migration fails

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(update_listener))

    # Initialize zone management
    await coordinator.async_initialize_zone_management()

    # Register services
    async def force_update(call: ServiceCall) -> None:
        """Force update of all entities."""
        try:
            # Check if specific entities are targeted
            entity_ids = call.data.get("entity_id")

            if entity_ids:
                # Handle specific entity targeting
                if isinstance(entity_ids, str):
                    entity_ids = [entity_ids]

                # Find coordinators for the specified entities
                updated_coordinators = set()
                entity_registry = er.async_get(hass)

                for entity_id in entity_ids:
                    # Find which coordinator owns this entity
                    for entry_id, coordinator in hass.data[DOMAIN].items():
                        if isinstance(coordinator, ActronDataCoordinator):
                            entries = er.async_entries_for_config_entry(
                                entity_registry, entry_id
                            )
                            coordinator_entity_ids = [
                                entry.entity_id for entry in entries
                            ]

                            if entity_id in coordinator_entity_ids:
                                if coordinator not in updated_coordinators:
                                    await coordinator.async_request_refresh()
                                    updated_coordinators.add(coordinator)
                                    _LOGGER.info(
                                        "Force update completed for device %s (entity: %s)",
                                        coordinator.device_id,
                                        entity_id,
                                    )
                                break
                    else:
                        _LOGGER.warning(
                            "Entity %s not found in any ActronAir coordinator",
                            entity_id,
                        )
            else:
                # No specific entities targeted, update all coordinators
                for coordinator in hass.data[DOMAIN].values():
                    if isinstance(coordinator, ActronDataCoordinator):
                        await coordinator.async_request_refresh()
                        _LOGGER.info(
                            "Force update completed for device %s",
                            coordinator.device_id,
                        )

        except Exception as err:
            _LOGGER.error("Error during force update: %s", err)

    async def create_zone_preset(call: ServiceCall) -> None:
        """Create a zone preset from current state."""
        device_id = call.data.get("device_id")
        preset_name = call.data.get("name")
        description = call.data.get("description", "")

        if not device_id or not preset_name:
            _LOGGER.error("Device ID and preset name are required")
            return

        # Find coordinator for device
        target_coordinator = None
        for coord in hass.data[DOMAIN].values():
            if (
                isinstance(coord, ActronDataCoordinator)
                and coord.device_id == device_id
            ):
                target_coordinator = coord
                break

        if not target_coordinator:
            _LOGGER.error("Device %s not found", device_id)
            return

        # Check if zone control is enabled
        if not target_coordinator.enable_zone_control:
            _LOGGER.error(
                "Zone control is not enabled for device %s. Zone presets are not available for single-zone systems.",
                device_id,
            )
            return

        try:
            await target_coordinator.async_create_zone_preset_from_current(
                preset_name, description
            )
            _LOGGER.info(
                "Created zone preset '%s' for device %s", preset_name, device_id
            )
        except (ConfigurationError, ZoneError) as err:
            _LOGGER.error("Failed to create zone preset: %s", err)

    async def apply_zone_preset(call: ServiceCall) -> None:
        """Apply a zone preset."""
        device_id = call.data.get("device_id")
        preset_name = call.data.get("name")

        if not device_id or not preset_name:
            _LOGGER.error("Device ID and preset name are required")
            return

        # Find coordinator for device
        target_coordinator = None
        for coord in hass.data[DOMAIN].values():
            if (
                isinstance(coord, ActronDataCoordinator)
                and coord.device_id == device_id
            ):
                target_coordinator = coord
                break

        if not target_coordinator:
            _LOGGER.error("Device %s not found", device_id)
            return

        # Check if zone control is enabled
        if not target_coordinator.enable_zone_control:
            _LOGGER.error(
                "Zone control is not enabled for device %s. Zone presets are not available for single-zone systems.",
                device_id,
            )
            return

        try:
            await target_coordinator.async_apply_zone_preset(preset_name)
            _LOGGER.info(
                "Applied zone preset '%s' for device %s", preset_name, device_id
            )
        except (ConfigurationError, ZoneError) as err:
            _LOGGER.error("Failed to apply zone preset: %s", err)

    async def bulk_zone_operation(call: ServiceCall) -> None:
        """Perform bulk zone operations."""
        device_id = call.data.get("device_id")
        operation = call.data.get("operation")
        zones = call.data.get("zones", [])

        if not device_id or not operation or not zones:
            _LOGGER.error("Device ID, operation, and zones are required")
            return

        # Find coordinator for device
        target_coordinator = None
        for coord in hass.data[DOMAIN].values():
            if (
                isinstance(coord, ActronDataCoordinator)
                and coord.device_id == device_id
            ):
                target_coordinator = coord
                break

        if not target_coordinator:
            _LOGGER.error("Device %s not found", device_id)
            return

        # Check if zone control is enabled
        if not target_coordinator.enable_zone_control:
            _LOGGER.error(
                "Zone control is not enabled for device %s. Bulk zone operations are not available for single-zone systems.",
                device_id,
            )
            return

        try:
            kwargs = {}
            if operation == "set_temperature":
                kwargs["temperature"] = call.data.get("temperature")
                kwargs["temp_key"] = call.data.get("temp_key", "temp_setpoint_cool")

            results = await target_coordinator.async_bulk_zone_operation(
                operation, zones, **kwargs
            )
            success_count = sum(1 for r in results if r["status"] == "success")
            _LOGGER.info(
                "Bulk operation '%s' completed: %d/%d zones successful",
                operation,
                success_count,
                len(zones),
            )
        except (ConfigurationError, ZoneError) as err:
            _LOGGER.error("Failed to perform bulk zone operation: %s", err)

    hass.services.async_register(DOMAIN, SERVICE_FORCE_UPDATE, force_update)
    hass.services.async_register(DOMAIN, "create_zone_preset", create_zone_preset)
    hass.services.async_register(DOMAIN, "apply_zone_preset", apply_zone_preset)
    hass.services.async_register(DOMAIN, "bulk_zone_operation", bulk_zone_operation)

    # Schedule repairs check
    hass.async_create_task(repairs.async_check_issues(hass, entry))

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
    new_enable_zone_control = entry.options.get(CONF_ENABLE_ZONE_CONTROL, False)

    try:
        if old_enable_zone_control and not new_enable_zone_control:
            _LOGGER.debug("Zone control being disabled, cleaning up entities")
            entity_registry = er.async_get(hass)
            entries = er.async_entries_for_config_entry(entity_registry, entry.entry_id)

            # First, remove entities from registry
            for entity_entry in entries:
                if entity_entry.unique_id.startswith(f"{coordinator.device_id}_zone_"):
                    _LOGGER.debug("Removing entity: %s", entity_entry.entity_id)
                    entity_registry.async_remove(entity_entry.entity_id)

            # Then update coordinator state
            await coordinator.set_enable_zone_control(new_enable_zone_control)

            # Finally, request a state refresh
            await coordinator.async_request_refresh()

        # Reload the config entry to apply changes
        await hass.config_entries.async_reload(entry.entry_id)
        _LOGGER.info(
            "Successfully updated zone control setting to: %s", new_enable_zone_control
        )

    except Exception as err:
        _LOGGER.error("Error updating zone control setting: %s", err)
        raise


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
