"""Support for ActronAir Neo switches."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ATTR_ZONE_NAME, ICON_ZONE
from .coordinator import ActronDataCoordinator

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ActronAir Neo switches from a config entry."""
    coordinator: ActronDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = [
        ActronAwayModeSwitch(coordinator),
        ActronQuietModeSwitch(coordinator),
    ]

    # Add zone switches
    for zone_id, zone_data in coordinator.data['zones'].items():
        entities.append(ActronZoneSwitch(coordinator, zone_id))

    async_add_entities(entities)

class ActronBaseSwitch(CoordinatorEntity, SwitchEntity):
    """Base class for ActronAir Neo switches."""

    def __init__(self, coordinator: ActronDataCoordinator, switch_type: str) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self.switch_type = switch_type
        self._attr_name = f"ActronAir Neo {switch_type.replace('_', ' ').title()}"
        self._attr_unique_id = f"{coordinator.device_id}_{switch_type}"

    @property
    def device_info(self):
        """Return device information about this entity."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.device_id)},
            "name": "ActronAir Neo",
            "manufacturer": "ActronAir",
            "model": self.coordinator.data["main"]["model"],
            "sw_version": self.coordinator.data["main"]["firmware_version"],
        }

class ActronAwayModeSwitch(ActronBaseSwitch):
    """Representation of an ActronAir Neo Away Mode switch."""

    def __init__(self, coordinator: ActronDataCoordinator) -> None:
        """Initialize the away mode switch."""
        super().__init__(coordinator, "away_mode")

    @property
    def is_on(self) -> bool:
        """Return true if away mode is on."""
        return self.coordinator.data["main"]["away_mode"]

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.coordinator.set_away_mode(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.coordinator.set_away_mode(False)

class ActronQuietModeSwitch(ActronBaseSwitch):
    """Representation of an Actron Neo Quiet Mode switch."""

    def __init__(self, coordinator: ActronDataCoordinator) -> None:
        """Initialize the quiet mode switch."""
        super().__init__(coordinator, "quiet_mode")

    @property
    def is_on(self) -> bool:
        """Return true if quiet mode is on."""
        return self.coordinator.data["main"]["quiet_mode"]

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.coordinator.set_quiet_mode(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.coordinator.set_quiet_mode(False)

class ActronZoneSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of an Actron Neo Zone switch."""

    def __init__(self, coordinator: ActronDataCoordinator, zone_id: str) -> None:
        """Initialize the zone switch."""
        super().__init__(coordinator)
        self.zone_id = zone_id
        self.zone_index = int(zone_id.split('_')[1]) - 1  # Convert to zero-based index
        self._attr_name = f"ActronAir Neo Zone {coordinator.data['zones'][zone_id]['name']}"
        self._attr_unique_id = f"{coordinator.device_id}_zone_{zone_id}"
        self._attr_icon = ICON_ZONE

    @property
    def is_on(self) -> bool:
        """Return true if the zone is enabled."""
        return self.coordinator.data['zones'][self.zone_id]['is_enabled']

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the zone on."""
        await self.coordinator.set_zone_state(self.zone_index, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the zone off."""
        await self.coordinator.set_zone_state(self.zone_index, False)

    @property
    def device_info(self):
        """Return device information about this entity."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.device_id)},
            "name": "ActronAir Neo",
            "manufacturer": "ActronAir",
            "model": self.coordinator.data["main"]["model"],
            "sw_version": self.coordinator.data["main"]["firmware_version"],
        }

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        zone_data = self.coordinator.data['zones'][self.zone_id]
        return {
            ATTR_ZONE_NAME: zone_data['name'],
            "temperature": zone_data.get('temp'),
            "humidity": zone_data.get('humidity'),
        }