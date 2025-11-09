"""Number platform for ActronAir Neo integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.number import NumberEntity  # type: ignore
from homeassistant.config_entries import ConfigEntry  # type: ignore
from homeassistant.core import HomeAssistant  # type: ignore
from homeassistant.helpers.entity import EntityCategory  # type: ignore
from homeassistant.helpers.entity_platform import AddEntitiesCallback  # type: ignore

from .const import DOMAIN
from .coordinator import ActronDataCoordinator

if TYPE_CHECKING:
    from .coordinator import ActronDataCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ActronAir Neo number entities."""
    coordinator: ActronDataCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for zone_id, zone_data in coordinator.data["zones"].items():
        # Only create airflow control for zones with YourZone enabled
        if zone_data.get("airflow_control_enabled"):
            entities.append(ActronZoneAirflowNumber(coordinator, zone_id))
            _LOGGER.debug(
                "Creating YourZone airflow number entity for %s (zone_id: %s)",
                zone_data.get("name"),
                zone_id,
            )

    if entities:
        _LOGGER.info("Setting up %d YourZone airflow number entities", len(entities))
        async_add_entities(entities)
    else:
        _LOGGER.info("No zones with YourZone enabled found")


class ActronZoneAirflowNumber(NumberEntity):
    """Number entity for zone airflow control (YourZone)."""

    _attr_has_entity_name = True
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 5
    _attr_native_unit_of_measurement = "%"
    _attr_icon = "mdi:air-filter"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: ActronDataCoordinator, zone_id: str) -> None:
        """Initialize the number entity."""
        self.coordinator = coordinator
        self.zone_id = zone_id
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.device_id)},
            "name": "ActronAir Neo",
            "manufacturer": "ActronAir",
            "model": coordinator.data["main"].get("model", "Unknown"),
        }

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        zone_name = self.coordinator.data["zones"][self.zone_id]["name"]
        return f"{zone_name} Airflow"

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{self.coordinator.device_id}_{self.zone_id}_airflow"

    @property
    def native_value(self) -> float | None:
        """Return the current airflow setpoint."""
        return self.coordinator.data["zones"][self.zone_id].get("airflow_setpoint")

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        zone_data = self.coordinator.data["zones"][self.zone_id]
        return (
            self.coordinator.last_update_success
            and zone_data.get("airflow_control_enabled", False)
            and not zone_data.get("airflow_control_locked", False)
        )

    async def async_set_native_value(self, value: float) -> None:
        """Set new airflow percentage."""
        zone_index = int(self.zone_id.split("_")[1]) - 1
        _LOGGER.info(
            "Setting airflow for zone %s (%s) to %d%%",
            self.zone_id,
            self.coordinator.data["zones"][self.zone_id]["name"],
            int(value),
        )
        try:
            await self.coordinator.api.set_zone_airflow(zone_index, int(value))
            await self.coordinator.async_request_refresh()
        except (ValueError, IndexError) as err:
            _LOGGER.error("Failed to set zone airflow: %s", err)
            raise

    @property
    def should_poll(self) -> bool:
        """No need to poll. Coordinator notifies entity of updates."""
        return False

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update(self) -> None:
        """Update the entity. Only used by the generic entity update service."""
        await self.coordinator.async_request_refresh()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        zone_data = self.coordinator.data["zones"][self.zone_id]
        return {
            "zone_id": self.zone_id,
            "zone_name": zone_data.get("name"),
            "yourzone_enabled": zone_data.get("airflow_control_enabled"),
            "yourzone_locked": zone_data.get("airflow_control_locked"),
            "zone_max_position": zone_data.get("zone_max_position"),
            "zone_min_position": zone_data.get("zone_min_position"),
        }
