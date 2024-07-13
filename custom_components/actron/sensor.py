import logging
from typing import Any, Dict, Optional

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
    SensorDeviceClass,
)
from homeassistant.const import (
    UnitOfTemperature,
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = []

    # Main system sensors
    entities.extend([
        ActronTemperatureSensor(coordinator, "main", "indoor"),
        ActronTemperatureSensor(coordinator, "main", "outdoor"),
        ActronHumiditySensor(coordinator, "main"),
    ])

    # Zone sensors
    for zone_id in coordinator.data["zones"]:
        entities.extend([
            ActronTemperatureSensor(coordinator, zone_id, "zone"),
            ActronHumiditySensor(coordinator, zone_id),
        ])

    # Peripheral sensors
    for peripheral_id in coordinator.data["peripherals"]:
        entities.extend([
            ActronTemperatureSensor(coordinator, peripheral_id, "peripheral"),
            ActronHumiditySensor(coordinator, peripheral_id),
            ActronBatterySensor(coordinator, peripheral_id),
            ActronSignalStrengthSensor(coordinator, peripheral_id),
        ])

    async_add_entities(entities, True)

class ActronSensorBase(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, sensor_id: str, name: str, device_class: str, state_class: str, unit: str):
        super().__init__(coordinator)
        self._sensor_id = sensor_id
        self._attr_name = f"Actron Air Neo {sensor_id} {name}"
        self._attr_unique_id = f"{DOMAIN}_{coordinator.device_id}_{sensor_id}_{name.lower().replace(' ', '_')}"
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
    def __init__(self, coordinator, sensor_id: str, sensor_type: str):
        super().__init__(
            coordinator,
            sensor_id,
            f"{sensor_type.capitalize()} Temperature",
            SensorDeviceClass.TEMPERATURE,
            SensorStateClass.MEASUREMENT,
            UnitOfTemperature.CELSIUS,
        )
        self._sensor_type = sensor_type

    @property
    def native_value(self) -> Optional[float]:
        if self._sensor_type == "main":
            return self.coordinator.data["main"]["indoor_temp" if self._sensor_id == "main" else "outdoor_temp"]
        elif self._sensor_type == "zone":
            return self.coordinator.data["zones"][self._sensor_id]["temp"]
        elif self._sensor_type == "peripheral":
            return self.coordinator.data["peripherals"][self._sensor_id]["temp"]

class ActronHumiditySensor(ActronSensorBase):
    def __init__(self, coordinator, sensor_id: str):
        super().__init__(
            coordinator,
            sensor_id,
            "Humidity",
            SensorDeviceClass.HUMIDITY,
            SensorStateClass.MEASUREMENT,
            PERCENTAGE,
        )

    @property
    def native_value(self) -> Optional[float]:
        if self._sensor_id == "main":
            return self.coordinator.data["main"]["indoor_humidity"]
        elif self._sensor_id in self.coordinator.data["zones"]:
            return self.coordinator.data["zones"][self._sensor_id]["humidity"]
        elif self._sensor_id in self.coordinator.data["peripherals"]:
            return self.coordinator.data["peripherals"][self._sensor_id]["humidity"]

class ActronBatterySensor(ActronSensorBase):
    def __init__(self, coordinator, sensor_id: str):
        super().__init__(
            coordinator,
            sensor_id,
            "Battery",
            SensorDeviceClass.BATTERY,
            SensorStateClass.MEASUREMENT,
            PERCENTAGE,
        )

    @property
    def native_value(self) -> Optional[float]:
        return self.coordinator.data["peripherals"][self._sensor_id]["battery_level"]

class ActronSignalStrengthSensor(ActronSensorBase):
    def __init__(self, coordinator, sensor_id: str):
        super().__init__(
            coordinator,
            sensor_id,
            "Signal Strength",
            SensorDeviceClass.SIGNAL_STRENGTH,
            SensorStateClass.MEASUREMENT,
            SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        )

    @property
    def native_value(self) -> Optional[float]:
        return self.coordinator.data["peripherals"][self._sensor_id]["signal_strength"]