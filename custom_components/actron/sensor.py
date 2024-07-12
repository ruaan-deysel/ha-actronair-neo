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
from .coordinator import ActronDataCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = [
        ActronTemperatureSensor(coordinator, "indoor"),
        ActronTemperatureSensor(coordinator, "outdoor"),
        ActronHumiditySensor(coordinator),
        ActronBatterySensor(coordinator),
    ]

    async_add_entities(entities, True)

class ActronSensorBase(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator: ActronDataCoordinator, name: str, device_class: str, state_class: str, unit: str):
        super().__init__(coordinator)
        self._attr_name = f"Actron Air Neo {name}"
        self._attr_unique_id = f"{DOMAIN}_{name.lower().replace(' ', '_')}"
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_native_unit_of_measurement = unit

    @property
    def device_info(self) -> Dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self.coordinator.device_id)},
            "name": "Actron Air Neo",
            "manufacturer": "Actron Air",
            "model": "Neo",
        }

class ActronTemperatureSensor(ActronSensorBase):
    def __init__(self, coordinator: ActronDataCoordinator, sensor_type: str):
        super().__init__(
            coordinator,
            f"{sensor_type.capitalize()} Temperature",
            SensorDeviceClass.TEMPERATURE,
            SensorStateClass.MEASUREMENT,
            UnitOfTemperature.CELSIUS,
        )
        self._sensor_type = sensor_type

    @property
    def native_value(self) -> Optional[float]:
        attr = ATTR_INDOOR_TEMPERATURE if self._sensor_type == "indoor" else ATTR_OUTDOOR_TEMPERATURE
        return self.coordinator.data.get(attr)

class ActronHumiditySensor(ActronSensorBase):
    def __init__(self, coordinator: ActronDataCoordinator):
        super().__init__(
            coordinator,
            "Humidity",
            SensorDeviceClass.HUMIDITY,
            SensorStateClass.MEASUREMENT,
            PERCENTAGE,
        )

    @property
    def native_value(self) -> Optional[float]:
        return self.coordinator.data.get("indoor_humidity")

class ActronBatterySensor(ActronSensorBase):
    def __init__(self, coordinator: ActronDataCoordinator):
        super().__init__(
            coordinator,
            "Battery",
            SensorDeviceClass.BATTERY,
            SensorStateClass.MEASUREMENT,
            PERCENTAGE,
        )

    @property
    def native_value(self) -> Optional[float]:
        return self.coordinator.data.get("battery_level")