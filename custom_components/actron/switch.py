from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ActronDataCoordinator

import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the Actron Air Neo zone switches."""
    coordinator: ActronDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []

    for zone_id in coordinator.data["zones"]:
        entities.append(ActronZoneSwitch(coordinator, zone_id))

    async_add_entities(entities)

class ActronZoneSwitch(CoordinatorEntity, SwitchEntity):
    def __init__(self, coordinator: ActronDataCoordinator, zone_id: str):
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._attr_name = f"Actron Air Neo Zone {zone_id}"
        self._attr_unique_id = f"{DOMAIN}_{coordinator.device_id}_zone_{zone_id}"

    @property
    def is_on(self) -> bool:
        return self.coordinator.data['zones'][self._zone_id]['is_enabled']

    async def async_turn_on(self, **kwargs):
        await self.coordinator.api.send_command(self.coordinator.device_id, {
            f"UserAirconSettings.EnabledZones[{self._zone_id}]": True
        })
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        await self.coordinator.api.send_command(self.coordinator.device_id, {
            f"UserAirconSettings.EnabledZones[{self._zone_id}]": False
        })
        await self.coordinator.async_request_refresh()

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.coordinator.device_id)},
            "name": f"Actron Air Neo",
            "manufacturer": "Actron Air",
            "model": "Neo",
        }