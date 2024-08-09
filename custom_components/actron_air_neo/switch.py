"""Support for Actron Air Neo switches."""
from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, DEVICE_MANUFACTURER, DEVICE_MODEL
from .coordinator import ActronDataCoordinator

import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """Set up Actron Neo switches from a config entry."""
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
    """Base class for Actron Neo switches."""

    def __init__(self, coordinator: ActronDataCoordinator, switch_type: str):
        super().__init__(coordinator)
        self.switch_type = switch_type
        self._attr_name = f"ActronAir {switch_type.replace('_', ' ').title()}"
        self._attr_unique_id = f"{coordinator.device_id}_{switch_type}"

    @property
    def is_on(self):
        """Return true if the switch is on."""
        return self.coordinator.data['main'].get(self.switch_type, False)

    @property
    def device_info(self):
        """Return device information about this entity."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.device_id)},
            "name": "ActronAir Neo",
            "manufacturer": DEVICE_MANUFACTURER,
            "model": DEVICE_MODEL,
            "sw_version": self.coordinator.data['main'].get('firmware_version'),
        }

class ActronAwayModeSwitch(ActronBaseSwitch):
    """Representation of an Actron Neo Away Mode switch."""

    def __init__(self, coordinator: ActronDataCoordinator):
        super().__init__(coordinator, "away_mode")

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        await self.coordinator.set_away_mode(True)

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        await self.coordinator.set_away_mode(False)

class ActronQuietModeSwitch(ActronBaseSwitch):
    """Representation of an Actron Neo Quiet Mode switch."""

    def __init__(self, coordinator: ActronDataCoordinator):
        super().__init__(coordinator, "quiet_mode")

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        await self.coordinator.set_quiet_mode(True)

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        await self.coordinator.set_quiet_mode(False)

class ActronContinuousFanSwitch(ActronBaseSwitch):
    """Representation of an Actron Neo Continuous Fan switch."""

    def __init__(self, coordinator: ActronDataCoordinator):
        super().__init__(coordinator, "continuous_fan")

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        await self.coordinator.set_continuous_fan(True)

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        await self.coordinator.set_continuous_fan(False)

class ActronZoneSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of an Actron Neo Zone switch."""

    def __init__(self, coordinator: ActronDataCoordinator, zone_id: str):
        super().__init__(coordinator)
        self.zone_id = zone_id
        self._attr_name = f"ActronAir Zone {coordinator.data['zones'][zone_id]['name']}"
        self._attr_unique_id = f"{coordinator.device_id}_zone_{zone_id}"

    @property
    def is_on(self):
        """Return true if the zone is enabled."""
        return self.coordinator.data['zones'][self.zone_id]['is_enabled']

    async def async_turn_on(self, **kwargs):
        """Turn the zone on."""
        zone_index = int(self.zone_id.split('_')[1]) - 1
        await self.coordinator.set_zone_state(zone_index, True)

    async def async_turn_off(self, **kwargs):
        """Turn the zone off."""
        zone_index = int(self.zone_id.split('_')[1]) - 1
        await self.coordinator.set_zone_state(zone_index, False)

    @property
    def device_info(self):
        """Return device information about this entity."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.device_id)},
            "name": "ActronAir Neo",
            "manufacturer": DEVICE_MANUFACTURER,
            "model": DEVICE_MODEL,
            "sw_version": self.coordinator.data['main'].get('firmware_version'),
        }

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        zone_data = self.coordinator.data['zones'][self.zone_id]
        return {
            "temperature": zone_data.get('temp'),
            "humidity": zone_data.get('humidity'),
            "temperature_setpoint_cool": zone_data.get('temp_setpoint_cool'),
            "temperature_setpoint_heat": zone_data.get('temp_setpoint_heat'),
        }