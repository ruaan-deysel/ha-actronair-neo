import logging
from typing import Any, Dict, Optional

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
    SensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfTemperature,
    PERCENTAGE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    ATTR_INDOOR_TEMPERATURE,
    ATTR_OUTDOOR_TEMPERATURE,
    ATTR_FILTER_LIFE,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = []

    for system_id, system_data in coordinator.data.items():
        entities.extend([
            ActronTemperatureSensor(coordinator, system_id, "indoor"),
            ActronTemperatureSensor(coordinator, system_id, "outdoor"),
            ActronHumiditySensor(coordinator, system_id),
            ActronBatterySensor(coordinator, system_id),
        ])

        # Add zone sensors
        for zone_id, zone_data in system_data.get("zones", {}).items():
            entities.append(ActronZoneTemperatureSensor(coordinator, system_id, zone_id))

    async_add_entities(entities, True)

class ActronSensorBase(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, system_id: str, name: str, device_class: str, state_class: str, unit: str):
        super().__init__(coordinator)
        self._system_id = system_id
        self._attr_name = f"{coordinator.data[system_id]['name']} {name}"
        self._attr_unique_id = f"{DOMAIN}_{system_id}_{name.lower().replace(' ', '_')}"
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_native_unit_of_measurement = unit

    @property
    def device_info(self) -> Dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._system_id)},
            "name": self.coordinator.data[self._system_id]["name"],
            "manufacturer": "Actron Air",
            "model": "Neo",
        }

class ActronTemperatureSensor(ActronSensorBase):
    def __init__(self, coordinator, system_id: str, sensor_type: str):
        super().__init__(
            coordinator,
            system_id,
            f"{sensor_type.capitalize()} Temperature",
            SensorDeviceClass.TEMPERATURE,
            SensorStateClass.MEASUREMENT,
            UnitOfTemperature.CELSIUS,
        )
        self._sensor_type = sensor_type

    @property
    def native_value(self) -> Optional[float]:
        attr = ATTR_INDOOR_TEMPERATURE if self._sensor_type == "indoor" else ATTR_OUTDOOR_TEMPERATURE
        return self.coordinator.data[self._system_id].get(attr)

class ActronHumiditySensor(ActronSensorBase):
    def __init__(self, coordinator, system_id: str):
        super().__init__(
            coordinator,
            system_id,
            "Humidity",
            SensorDeviceClass.HUMIDITY,
            SensorStateClass.MEASUREMENT,
            PERCENTAGE,
        )

    @property
    def native_value(self) -> Optional[float]:
        return self.coordinator.data[self._system_id].get("indoor_humidity")

class ActronBatterySensor(ActronSensorBase):
    def __init__(self, coordinator, system_id: str):
        super().__init__(
            coordinator,
            system_id,
            "Battery",
            SensorDeviceClass.BATTERY,
            SensorStateClass.MEASUREMENT,
            PERCENTAGE,
        )

    @property
    def native_value(self) -> Optional[float]:
        return self.coordinator.data[self._system_id].get("battery_level")

class ActronZoneTemperatureSensor(ActronSensorBase):
    def __init__(self, coordinator, system_id: str, zone_id: str):
        zone_name = coordinator.data[system_id]["zones"][zone_id]["name"]
        super().__init__(
            coordinator,
            system_id,
            f"Zone {zone_name} Temperature",
            SensorDeviceClass.TEMPERATURE,
            SensorStateClass.MEASUREMENT,
            UnitOfTemperature.CELSIUS,
        )
        self._zone_id = zone_id

    @property
    def native_value(self) -> Optional[float]:
        return self.coordinator.data[self._system_id]["zones"][self._zone_id]["temperature"]

    @property
    def available(self) -> bool:
        return (
            super().available
            and self.coordinator.data[self._system_id]["zones"][self._zone_id]["enabled"]
        )