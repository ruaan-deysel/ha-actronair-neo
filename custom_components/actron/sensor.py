"""Support for Actron Air Neo sensors."""
from __future__ import annotations

import logging
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ActronDataCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Actron Air Neo sensors."""
    coordinator: ActronDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = []

    # Main system sensors
    entities.extend([
        ActronTemperatureSensor(coordinator, "main", "indoor"),
        ActronTemperatureSensor(coordinator, "main", "outdoor"),
        ActronHumiditySensor(coordinator, "main"),
        ActronModeSensor(coordinator),
        ActronFanModeSensor(coordinator),
        ActronAwayModeSensor(coordinator),
        ActronQuietModeSensor(coordinator),
    ])

    # Zone sensors
    for zone_id in coordinator.data["zones"]:
        entities.extend([
            ActronTemperatureSensor(coordinator, zone_id, "zone"),
            ActronHumiditySensor(coordinator, zone_id),
            ActronZoneEnabledSensor(coordinator, zone_id),
        ])

    # Peripheral sensors
    for peripheral_id in coordinator.data["peripherals"]:
        entities.extend([
            ActronTemperatureSensor(coordinator, peripheral_id, "peripheral"),
            ActronHumiditySensor(coordinator, peripheral_id),
            ActronBatterySensor(coordinator, peripheral_id),
            ActronSignalStrengthSensor(coordinator, peripheral_id),
        ])

    async_add_entities(entities)

class ActronSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for Actron Air Neo sensors."""

    def __init__(
        self,
        coordinator: ActronDataCoordinator,
        sensor_id: str,
        name: str,
        device_class: SensorDeviceClass | None,
        state_class: SensorStateClass | str | None,
        native_unit_of_measurement: str | None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor_id = sensor_id
        self._attr_name = f"Actron Air Neo {sensor_id} {name}"
        self._attr_unique_id = f"{DOMAIN}_{coordinator.device_id}_{sensor_id}_{name.lower().replace(' ', '_')}"
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_native_unit_of_measurement = native_unit_of_measurement

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information about this entity."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.device_id)},
            "name": "Actron Air Neo",
            "manufacturer": "Actron Air",
            "model": "Neo",
        }

class ActronTemperatureSensor(ActronSensorBase):
    """Representation of an Actron Air Neo temperature sensor."""

    def __init__(
        self,
        coordinator: ActronDataCoordinator,
        sensor_id: str,
        sensor_type: str,
    ) -> None:
        """Initialize the temperature sensor."""
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
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        try:
            if self._sensor_type == "main":
                return self.coordinator.data["main"]["indoor_temp" if self._sensor_id == "main" else "outdoor_temp"]
            elif self._sensor_type == "zone":
                return self.coordinator.data["zones"][self._sensor_id]["temp"]
            elif self._sensor_type == "peripheral":
                return self.coordinator.data["peripherals"][self._sensor_id]["temp"]
        except KeyError:
            _LOGGER.error("Failed to get temperature for %s", self._sensor_id)
        return None

class ActronHumiditySensor(ActronSensorBase):
    """Representation of an Actron Air Neo humidity sensor."""

    def __init__(
        self,
        coordinator: ActronDataCoordinator,
        sensor_id: str,
    ) -> None:
        """Initialize the humidity sensor."""
        super().__init__(
            coordinator,
            sensor_id,
            "Humidity",
            SensorDeviceClass.HUMIDITY,
            SensorStateClass.MEASUREMENT,
            PERCENTAGE,
        )

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        try:
            if self._sensor_id == "main":
                return self.coordinator.data["main"]["indoor_humidity"]
            elif self._sensor_id in self.coordinator.data["zones"]:
                return self.coordinator.data["zones"][self._sensor_id]["humidity"]
            elif self._sensor_id in self.coordinator.data["peripherals"]:
                return self.coordinator.data["peripherals"][self._sensor_id]["humidity"]
        except KeyError:
            _LOGGER.error("Failed to get humidity for %s", self._sensor_id)
        return None

class ActronModeSensor(ActronSensorBase):
    """Representation of an Actron Air Neo mode sensor."""

    def __init__(self, coordinator: ActronDataCoordinator) -> None:
        """Initialize the mode sensor."""
        super().__init__(
            coordinator,
            "main",
            "Mode",
            None,
            None,
            None,
        )

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        try:
            return self.coordinator.data["main"]["mode"]
        except KeyError:
            _LOGGER.error("Failed to get mode")
        return None

class ActronFanModeSensor(ActronSensorBase):
    """Representation of an Actron Air Neo fan mode sensor."""

    def __init__(self, coordinator: ActronDataCoordinator) -> None:
        """Initialize the fan mode sensor."""
        super().__init__(
            coordinator,
            "main",
            "Fan Mode",
            None,
            None,
            None,
        )

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        try:
            return self.coordinator.data["main"]["fan_mode"]
        except KeyError:
            _LOGGER.error("Failed to get fan mode")
        return None

class ActronAwayModeSensor(ActronSensorBase):
    """Representation of an Actron Air Neo away mode sensor."""

    def __init__(self, coordinator: ActronDataCoordinator) -> None:
        """Initialize the away mode sensor."""
        super().__init__(
            coordinator,
            "main",
            "Away Mode",
            SensorDeviceClass.ENUM,
            None,
            None,
        )

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        try:
            return "On" if self.coordinator.data["main"]["away_mode"] else "Off"
        except KeyError:
            _LOGGER.error("Failed to get away mode status")
        return None

    @property
    def options(self) -> list[str]:
        """Return the list of available options."""
        return ["On", "Off"]

class ActronQuietModeSensor(ActronSensorBase):
    """Representation of an Actron Air Neo quiet mode sensor."""

    def __init__(self, coordinator: ActronDataCoordinator) -> None:
        """Initialize the quiet mode sensor."""
        super().__init__(
            coordinator,
            "main",
            "Quiet Mode",
            SensorDeviceClass.ENUM,
            None,
            None,
        )

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        try:
            return "On" if self.coordinator.data["main"]["quiet_mode_active"] else "Off"
        except KeyError:
            _LOGGER.error("Failed to get quiet mode status")
        return None

    @property
    def options(self) -> list[str]:
        """Return the list of available options."""
        return ["On", "Off"]

class ActronZoneEnabledSensor(ActronSensorBase):
    """Representation of an Actron Air Neo zone enabled sensor."""

    def __init__(
        self,
        coordinator: ActronDataCoordinator,
        zone_id: str,
    ) -> None:
        """Initialize the zone enabled sensor."""
        super().__init__(
            coordinator,
            zone_id,
            "Zone Enabled",
            SensorDeviceClass.ENUM,
            None,
            None,
        )
        self._zone_id = zone_id

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        try:
            return "Enabled" if self.coordinator.data["zones"][self._zone_id]["is_enabled"] else "Disabled"
        except KeyError:
            _LOGGER.error("Failed to get zone enabled status for %s", self._zone_id)
        return None

    @property
    def options(self) -> list[str]:
        """Return the list of available options."""
        return ["Enabled", "Disabled"]

class ActronBatterySensor(ActronSensorBase):
    """Representation of an Actron Air Neo battery sensor."""

    def __init__(
        self,
        coordinator: ActronDataCoordinator,
        sensor_id: str,
    ) -> None:
        """Initialize the battery sensor."""
        super().__init__(
            coordinator,
            sensor_id,
            "Battery",
            SensorDeviceClass.BATTERY,
            SensorStateClass.MEASUREMENT,
            PERCENTAGE,
        )

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        try:
            return self.coordinator.data["peripherals"][self._sensor_id]["battery_level"]
        except KeyError:
            _LOGGER.error("Failed to get battery level for %s", self._sensor_id)
        return None

class ActronSignalStrengthSensor(ActronSensorBase):
    """Representation of an Actron Air Neo signal strength sensor."""

    def __init__(
        self,
        coordinator: ActronDataCoordinator,
        sensor_id: str,
    ) -> None:
        """Initialize the signal strength sensor."""
        super().__init__(
            coordinator,
            sensor_id,
            "Signal Strength",
            SensorDeviceClass.SIGNAL_STRENGTH,
            SensorStateClass.MEASUREMENT,
            SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        )

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        try:
            return self.coordinator.data["peripherals"][self._sensor_id]["signal_strength"]
        except KeyError:
            _LOGGER.error("Failed to get signal strength for %s", self._sensor_id)
        return None