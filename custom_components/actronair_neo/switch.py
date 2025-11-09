"""Support for ActronAir Neo switches."""

from __future__ import annotations

import asyncio
import datetime
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchEntity  # type: ignore
from homeassistant.helpers.update_coordinator import CoordinatorEntity  # type: ignore

from .base_entity import ActronEntityBase
from .const import DOMAIN, ICON_ZONE

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

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
    for zone_id in coordinator.data["zones"]:
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


class ActronAwayModeSwitch(ActronEntityBase, SwitchEntity):
    """Away mode switch."""

    def __init__(self, coordinator: ActronDataCoordinator) -> None:
        """Initialize the away mode switch."""
        super().__init__(coordinator, "switch", "Away Mode")
        self._attr_icon = "mdi:home-export-outline"

    @property
    def is_on(self) -> bool:
        """Return true if away mode is on."""
        return self.coordinator.data["main"]["away_mode"]

    async def async_turn_on(self) -> None:
        """Turn the switch on."""
        await self.coordinator.set_away_mode(True)

    async def async_turn_off(self) -> None:
        """Turn the switch off."""
        await self.coordinator.set_away_mode(False)


class ActronQuietModeSwitch(ActronEntityBase, SwitchEntity):
    """Quiet mode switch."""

    def __init__(self, coordinator: ActronDataCoordinator) -> None:
        """Initialize the quiet mode switch."""
        super().__init__(coordinator, "switch", "Quiet Mode")
        self._attr_icon = "mdi:volume-mute"

    @property
    def is_on(self) -> bool:
        """Return true if quiet mode is on."""
        return self.coordinator.data["main"]["quiet_mode"]

    async def async_turn_on(self) -> None:
        """Turn the switch on."""
        await self.coordinator.set_quiet_mode(True)

    async def async_turn_off(self) -> None:
        """Turn the switch off."""
        await self.coordinator.set_quiet_mode(False)


class ActronContinuousFanSwitch(ActronEntityBase, SwitchEntity):
    """Continuous fan mode switch."""

    def __init__(self, coordinator: ActronDataCoordinator) -> None:
        """Initialize the continuous fan mode switch."""
        super().__init__(coordinator, "switch", "Continuous Fan")
        self._attr_icon = "mdi:fan-clock"

    @property
    def is_on(self) -> bool:
        """Return true if continuous fan mode is on."""
        current_mode = self.coordinator.data["main"].get("fan_mode", "")
        return "+CONT" in current_mode

    async def async_turn_on(self) -> None:
        """Turn the switch on."""
        try:
            # Get current fan mode and strip any existing suffixes
            current_mode = self.coordinator.data["main"].get("fan_mode", "")
            base_mode = (
                current_mode.split("+")[0] if "+" in current_mode else current_mode
            )
            base_mode = base_mode.split("-")[0] if "-" in base_mode else base_mode

            # Validate base mode
            valid_modes = ["LOW", "MED", "HIGH", "AUTO"]
            if base_mode not in valid_modes:
                _LOGGER.warning(
                    "Invalid fan mode %s, using current base mode", base_mode
                )
                base_mode = self.coordinator.data["main"].get("base_fan_mode", "LOW")
                if base_mode not in valid_modes:
                    _LOGGER.warning(
                        "Invalid base fan mode %s, defaulting to LOW", base_mode
                    )
                    base_mode = "LOW"

            _LOGGER.debug("Turning on continuous mode with base mode: %s", base_mode)

            # Set fan mode with continuous enabled
            await self.coordinator.set_fan_mode(base_mode, True)

            # Request refresh to update state
            await asyncio.sleep(1)  # Short delay for API processing
            await self.coordinator.async_request_refresh()

            # Verify the change
            new_mode = self.coordinator.data["main"].get("fan_mode", "")
            if "+CONT" not in new_mode:
                _LOGGER.warning(
                    "Continuous mode did not activate as expected. Current mode: %s",
                    new_mode,
                )

        except Exception as err:
            _LOGGER.error(
                "Failed to turn on continuous fan mode: %s", str(err), exc_info=True
            )
            raise

    async def async_turn_off(self) -> None:
        """Turn the switch off."""
        try:
            # Get current fan mode and strip continuous suffix
            current_mode = self.coordinator.data["main"].get("fan_mode", "")
            base_mode = (
                current_mode.split("+")[0] if "+" in current_mode else current_mode
            )
            base_mode = base_mode.split("-")[0] if "-" in base_mode else base_mode

            # Validate base mode
            valid_modes = ["LOW", "MED", "HIGH", "AUTO"]
            if base_mode not in valid_modes:
                _LOGGER.warning(
                    "Invalid fan mode %s, using current base mode", base_mode
                )
                base_mode = self.coordinator.data["main"].get("base_fan_mode", "LOW")
                if base_mode not in valid_modes:
                    _LOGGER.warning(
                        "Invalid base fan mode %s, defaulting to LOW", base_mode
                    )
                    base_mode = "LOW"

            _LOGGER.debug(
                "Turning off continuous mode, maintaining base mode: %s", base_mode
            )

            # Set fan mode with continuous disabled
            await self.coordinator.set_fan_mode(base_mode, False)

            # Request refresh to update state
            await asyncio.sleep(1)  # Short delay for API processing
            await self.coordinator.async_request_refresh()

            # Verify the change
            new_mode = self.coordinator.data["main"].get("fan_mode", "")
            if "+CONT" in new_mode:
                _LOGGER.warning(
                    "Continuous mode did not deactivate as expected. Current mode: %s",
                    new_mode,
                )

        except Exception as err:
            _LOGGER.error(
                "Failed to turn off continuous fan mode: %s", str(err), exc_info=True
            )
            raise

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        current_mode = self.coordinator.data["main"].get("fan_mode", "")
        base_mode = current_mode.split("+")[0] if "+" in current_mode else current_mode

        return {
            "base_fan_mode": base_mode,
            "fan_mode": current_mode,
            "last_update": datetime.datetime.now().isoformat(),
        }


class ActronZoneSwitch(ActronEntityBase, SwitchEntity):
    """Zone switch."""

    def __init__(self, coordinator: ActronDataCoordinator, zone_id: str) -> None:
        """Initialize the zone switch."""
        zone_name = coordinator.data["zones"][zone_id]["name"]
        super().__init__(coordinator, "switch", f"Zone {zone_name}")
        self.zone_id = zone_id
        self.zone_index = int(zone_id.split("_")[1]) - 1
        self._attr_icon = ICON_ZONE

    @property
    def is_on(self) -> bool:
        """Return true if the zone is enabled."""
        return self.coordinator.data["zones"][self.zone_id]["is_enabled"]

    async def async_turn_on(self) -> None:
        """Turn the zone on."""
        await self.coordinator.set_zone_state(self.zone_index, True)

    async def async_turn_off(self) -> None:
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
