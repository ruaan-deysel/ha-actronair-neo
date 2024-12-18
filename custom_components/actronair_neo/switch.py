"""Support for ActronAir Neo switches."""
from __future__ import annotations
import datetime
import logging
import asyncio
from typing import Any

from homeassistant.components.switch import SwitchEntity # type: ignore
from homeassistant.config_entries import ConfigEntry # type: ignore
from homeassistant.core import HomeAssistant # type: ignore
from homeassistant.helpers.entity_platform import AddEntitiesCallback # type: ignore
from homeassistant.helpers.update_coordinator import CoordinatorEntity # type: ignore

from .const import DOMAIN, ICON_ZONE
from .coordinator import ActronDataCoordinator

_LOGGER = logging.getLogger(__name__)

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
        ActronContinuousFanSwitch(coordinator),
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
        self._attr_icon = "mdi:home-export-outline"

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
        self._attr_icon = "mdi:volume-mute"

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

class ActronContinuousFanSwitch(ActronBaseSwitch):
    """Representation of an ActronAir Neo Continuous Fan Mode switch."""

    def __init__(self, coordinator: ActronDataCoordinator) -> None:
        """Initialize the continuous fan mode switch."""
        super().__init__(coordinator, "continuous_fan")
        self._attr_name = "ActronAir Neo Continuous Fan"
        self._attr_icon = "mdi:fan-clock"

    @property
    def is_on(self) -> bool:
        """Return true if continuous fan mode is on."""
        return self.coordinator.data["main"].get("fan_continuous", False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        try:
            # Get current base fan mode from coordinator data
            fan_mode = self.coordinator.data["main"].get("base_fan_mode", "LOW")
            
            # Validate base mode
            valid_modes = ["LOW", "MED", "HIGH", "AUTO"]
            if fan_mode not in valid_modes:
                _LOGGER.warning("Invalid base fan mode %s, defaulting to LOW", fan_mode)
                fan_mode = "LOW"
                
            _LOGGER.debug("Turning on continuous mode with base mode: %s", fan_mode)
            
            # Set fan mode with continuous enabled
            await self.coordinator.set_fan_mode(fan_mode, True)
            
            # Request refresh to update state
            await asyncio.sleep(1)  # Short delay for API processing
            await self.coordinator.async_request_refresh()
            
            if not self.coordinator.data["main"].get("fan_continuous"):
                _LOGGER.warning("Continuous mode did not activate as expected")
                
        except Exception as err:
            _LOGGER.error(
                "Failed to turn on continuous fan mode: %s", 
                str(err), 
                exc_info=True
            )
            raise

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        try:
            # Get current base fan mode from coordinator data
            fan_mode = self.coordinator.data["main"].get("base_fan_mode", "LOW")
            
            # Validate base mode
            valid_modes = ["LOW", "MED", "HIGH", "AUTO"]
            if fan_mode not in valid_modes:
                _LOGGER.warning("Invalid base fan mode %s, defaulting to LOW", fan_mode)
                fan_mode = "LOW"
                
            _LOGGER.debug("Turning off continuous mode, maintaining base mode: %s", fan_mode)
            
            # Set fan mode with continuous disabled
            await self.coordinator.set_fan_mode(fan_mode, False)
            
            # Request refresh to update state
            await asyncio.sleep(1)  # Short delay for API processing
            await self.coordinator.async_request_refresh()
            
            if self.coordinator.data["main"].get("fan_continuous"):
                _LOGGER.warning("Continuous mode did not deactivate as expected")
                
        except Exception as err:
            _LOGGER.error(
                "Failed to turn off continuous fan mode: %s", 
                str(err), 
                exc_info=True
            )
            raise

        @property
        def extra_state_attributes(self) -> dict[str, Any]:
            """Return additional state attributes."""
            return {
                "base_fan_mode": self.coordinator.data["main"].get("base_fan_mode"),
                "fan_mode": self.coordinator.data["main"].get("fan_mode"),
                "last_update": datetime.now().isoformat(),
            }

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
