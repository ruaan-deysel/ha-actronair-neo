from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ActronDataCoordinator

import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """Set up Actron Neo zones from a config entry."""
    coordinator: ActronDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    zones = coordinator.data.get('zones', {})
    async_add_entities([ActronZone(coordinator, zone_id) for zone_id in zones])

class ActronZone(CoordinatorEntity, SwitchEntity):
    """Representation of an Actron Neo Zone."""

    def __init__(self, coordinator: ActronDataCoordinator, zone_id: str):
        super().__init__(coordinator)
        self.zone_id = zone_id
        self._attr_name = f"Actron Zone {coordinator.data['zones'][zone_id]['name']}"
        self._attr_unique_id = f"{coordinator.device_id}_zone_{zone_id}"

    @property
    def is_on(self) -> bool:
        """Return true if the zone is enabled."""
        return self.coordinator.data['zones'][self.zone_id]['is_enabled']

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success

    async def async_turn_on(self, **kwargs):
        """Turn the zone on."""
        _LOGGER.info("Turning on zone %s", self.name)
        try:
            await self.coordinator.set_zone_state(self.zone_id, True)
        except Exception as e:
            _LOGGER.error("Failed to turn on zone %s: %s", self.name, str(e))
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        """Turn the zone off."""
        _LOGGER.info("Turning off zone %s", self.name)
        try:
            await self.coordinator.set_zone_state(self.zone_id, False)
        except Exception as e:
            _LOGGER.error("Failed to turn off zone %s: %s", self.name, str(e))
        await self.coordinator.async_request_refresh()

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            "temperature": self.coordinator.data['zones'][self.zone_id].get('temp'),
            "humidity": self.coordinator.data['zones'][self.zone_id].get('humidity'),
        }