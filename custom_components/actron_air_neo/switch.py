"""Support for Actron Air Neo zones."""
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import ATTR_TEMPERATURE

from .const import DOMAIN
from .coordinator import ActronDataCoordinator

import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """Set up Actron Neo zones from a config entry."""
    coordinator: ActronDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    zones = coordinator.data.get('zones', {})
    _LOGGER.debug(f"Setting up {len(zones)} zones")
    entities = []
    for zone_id, zone_data in zones.items():
        entities.append(ActronZone(coordinator, zone_id))
    async_add_entities(entities)

class ActronZone(CoordinatorEntity, SwitchEntity):
    """Representation of an Actron Neo Zone."""

    def __init__(self, coordinator: ActronDataCoordinator, zone_id: str):
        super().__init__(coordinator)
        self.zone_id = zone_id
        self._attr_name = f"ActronAir Zone {coordinator.data['zones'][zone_id]['name']}"
        self._attr_unique_id = f"{coordinator.device_id}_zone_{zone_id}"
        self._attr_device_class = "switch"

    @property
    def is_on(self) -> bool:
        """Return true if the zone is enabled."""
        return self.coordinator.data['zones'].get(self.zone_id, {}).get('is_enabled', False)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.data is not None

    async def async_turn_on(self, **kwargs):
        """Turn the zone on."""
        _LOGGER.info("Turning on zone %s", self.name)
        try:
            await self.coordinator.set_zone_state(int(self.zone_id.split('_')[1]) - 1, True)
        except Exception as e:
            _LOGGER.error("Failed to turn on zone %s: %s", self.name, str(e))
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        """Turn the zone off."""
        _LOGGER.info("Turning off zone %s", self.name)
        try:
            await self.coordinator.set_zone_state(int(self.zone_id.split('_')[1]) - 1, False)
        except Exception as e:
            _LOGGER.error("Failed to turn off zone %s: %s", self.name, str(e))
        await self.coordinator.async_request_refresh()

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        if not self.coordinator.data or self.zone_id not in self.coordinator.data.get('zones', {}):
            return {}
        zone_data = self.coordinator.data['zones'][self.zone_id]
        return {
            "temperature": zone_data.get('temp'),
            "humidity": zone_data.get('humidity'),
            ATTR_TEMPERATURE: zone_data.get('temp_setpoint_cool'),  # Use cooling setpoint as default
            "temperature_setpoint_heat": zone_data.get('temp_setpoint_heat'),
            "temperature_setpoint_cool": zone_data.get('temp_setpoint_cool'),
        }

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self.coordinator.data['zones'].get(self.zone_id, {}).get('temp')

    @property
    def current_humidity(self):
        """Return the current humidity."""
        return self.coordinator.data['zones'].get(self.zone_id, {}).get('humidity')

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    async def async_update(self):
        """Update the entity."""
        await self.coordinator.async_request_refresh()

    def _handle_coordinator_update(self):
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()