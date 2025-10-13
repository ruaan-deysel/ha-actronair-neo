"""Support for ActronAir Neo climate devices."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (  # type: ignore
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.components.climate.const import (  # type: ignore
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
)
from homeassistant.config_entries import ConfigEntry  # type: ignore
from homeassistant.const import (  # type: ignore
    ATTR_TEMPERATURE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant  # type: ignore
from homeassistant.helpers import entity_registry as er  # type: ignore
from homeassistant.helpers.entity_platform import AddEntitiesCallback  # type: ignore

from .api import ApiError, ConfigurationError, ZoneError
from .base_entity import ActronEntityBase
from .const import (
    ADVANCE_FAN_MODES,
    ADVANCE_SERIES_MODELS,
    ADVANCED_FAN_MODE_ORDER,
    BASE_FAN_MODE_ORDER,
    BASE_FAN_MODES,
    DOMAIN,
    MAX_TEMP,
    MIN_TEMP,
)
from .coordinator import ActronDataCoordinator

_LOGGER = logging.getLogger(__name__)

HVAC_MODES = [
    HVACMode.OFF,
    HVACMode.COOL,
    HVACMode.HEAT,
    HVACMode.FAN_ONLY,
    HVACMode.AUTO,
]
FAN_MODES = [FAN_LOW, FAN_MEDIUM, FAN_HIGH, FAN_AUTO]

FAN_MODE_MAP = {
    FAN_LOW: "LOW",
    FAN_MEDIUM: "MED",
    FAN_HIGH: "HIGH",
    FAN_AUTO: "AUTO",
}

REVERSE_FAN_MODE_MAP = {v: k for k, v in FAN_MODE_MAP.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the ActronAir Neo climate device from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = [ActronClimate(coordinator)]

    entity_registry = er.async_get(hass)
    entries = er.async_entries_for_config_entry(entity_registry, config_entry.entry_id)

    if coordinator.enable_zone_control:
        for zone_id, _ in coordinator.data["zones"].items():
            entities.append(ActronZoneClimate(coordinator, zone_id))
    else:
        # Remove any existing zone climate entities
        for entry in entries:
            if entry.unique_id.startswith(f"{coordinator.device_id}_zone_"):
                entity_registry.async_remove(entry.entity_id)

    async_add_entities(entities, update_before_add=True)


class ActronClimate(ActronEntityBase, ClimateEntity):
    """Main climate entity with model-aware fan modes."""

    def __init__(self, coordinator: ActronDataCoordinator) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator, "climate")
        self._attr_name = self.DEVICE_NAME
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_hvac_modes = HVAC_MODES
        self._attr_min_temp = MIN_TEMP
        self._attr_max_temp = MAX_TEMP
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.FAN_MODE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        )

    @property
    def fan_modes(self) -> list[str]:
        """Return the list of available fan modes based on model capabilities."""
        try:
            model = self.coordinator.data["main"].get("model")
            supported_modes = self.coordinator.data["main"].get(
                "supported_fan_modes", BASE_FAN_MODES
            )
            if supported_modes == ADVANCE_FAN_MODES:
                supported_modes = ADVANCED_FAN_MODE_ORDER
            elif supported_modes == BASE_FAN_MODES:
                supported_modes = BASE_FAN_MODE_ORDER

            # Map Actron modes to HA modes
            mode_map = {
                "LOW": FAN_LOW,
                "MED": FAN_MEDIUM,
                "HIGH": FAN_HIGH,
                "AUTO": FAN_AUTO,
            }

            available_modes = []
            for mode in supported_modes:
                if ha_mode := mode_map.get(mode):
                    available_modes.append(ha_mode)

            _LOGGER.debug(
                "Available fan modes for model %s: %s (raw supported: %s)",
                model,
                available_modes,
                supported_modes,
            )

            return available_modes or [FAN_LOW, FAN_MEDIUM, FAN_HIGH]  # Fallback

        except Exception as err:
            _LOGGER.error("Error getting fan modes: %s", err, exc_info=True)
            return [FAN_LOW, FAN_MEDIUM, FAN_HIGH]  # Safe fallback

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self.coordinator.data["main"]["indoor_temp"]

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        if self.hvac_mode == HVACMode.COOL:
            return self.coordinator.data["main"]["temp_setpoint_cool"]
        if self.hvac_mode == HVACMode.HEAT:
            return self.coordinator.data["main"]["temp_setpoint_heat"]
        return None

    @property
    def hvac_mode(self) -> HVACMode:
        """Return hvac operation ie. heat, cool mode."""
        if not self.coordinator.data["main"]["is_on"]:
            return HVACMode.OFF
        mode = self.coordinator.data["main"]["mode"]
        return self._actron_to_ha_hvac_mode(mode)

    @property
    def fan_mode(self) -> str | None:
        """Return the fan setting."""
        actron_fan_mode = self.coordinator.data["main"]["fan_mode"]
        # Remove +CONT suffix and get base mode
        base_mode = actron_fan_mode.split("+")[0] if actron_fan_mode else "LOW"
        base_mode = base_mode.split("-")[0] if "-" in base_mode else base_mode
        return REVERSE_FAN_MODE_MAP.get(base_mode, FAN_LOW)

    @property
    def current_humidity(self) -> int | None:
        """Return the current humidity."""
        return self.coordinator.data["main"]["indoor_humidity"]

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        is_cooling = self.hvac_mode in [HVACMode.COOL, HVACMode.AUTO]
        await self.coordinator.set_temperature(temperature, is_cooling)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        if hvac_mode == self.hvac_mode:
            return  # No change needed

        if hvac_mode == HVACMode.OFF:
            command = self.coordinator.api.create_command("OFF")
        else:
            actron_mode = self._ha_to_actron_hvac_mode(hvac_mode)
            command = self.coordinator.api.create_command(
                "CLIMATE_MODE", mode=actron_mode
            )

        await self.coordinator.api.send_command(self.coordinator.device_id, command)
        await self.coordinator.async_request_refresh()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set fan mode with model-specific validation."""
        try:
            # Convert HA fan mode to Actron mode
            actron_mode = FAN_MODE_MAP.get(fan_mode, "LOW")

            # Get current continuous state
            current_fan_mode = self.coordinator.data["main"]["fan_mode"]
            continuous = "+CONT" in current_fan_mode

            # Check model support for AUTO mode
            model = self.coordinator.data["main"].get("model")
            if actron_mode == "AUTO" and model not in ADVANCE_SERIES_MODELS:
                _LOGGER.warning(
                    "Cannot set AUTO fan mode on model %s (Advance Series only)", model
                )
                return

            # Set fan mode while preserving continuous state
            await self.coordinator.set_fan_mode(actron_mode, continuous)

            _LOGGER.debug(
                "Set fan mode - Mode: %s, Continuous: %s, Model: %s, Result: %s",
                actron_mode,
                continuous,
                model,
                self.coordinator.data["main"]["fan_mode"],
            )

        except ValueError as err:
            # Handle specific error for unsupported AUTO mode
            if "AUTO fan mode is not supported" in str(err):
                _LOGGER.warning("Cannot set AUTO fan mode on non-Advance Series model")
            else:
                raise
        except Exception as err:
            _LOGGER.error("Failed to set fan mode %s: %s", fan_mode, err)
            raise

    async def async_turn_on(self) -> None:
        """Turn the entity on."""
        if self.hvac_mode != HVACMode.OFF:
            return  # Already on

        command = self.coordinator.api.create_command("ON")
        await self.coordinator.api.send_command(self.coordinator.device_id, command)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self) -> None:
        """Turn the entity off."""
        if self.hvac_mode == HVACMode.OFF:
            return  # Already off

        command = self.coordinator.api.create_command("OFF")
        await self.coordinator.api.send_command(self.coordinator.device_id, command)
        await self.coordinator.async_request_refresh()

    def _actron_to_ha_hvac_mode(self, mode: str) -> HVACMode:
        """Convert Actron HVAC mode to HA HVAC mode."""
        mode_map = {
            "AUTO": HVACMode.AUTO,
            "HEAT": HVACMode.HEAT,
            "COOL": HVACMode.COOL,
            "FAN": HVACMode.FAN_ONLY,
            "OFF": HVACMode.OFF,
        }
        return mode_map.get(mode.upper(), HVACMode.OFF)

    def _ha_to_actron_hvac_mode(self, mode: HVACMode) -> str:
        """Convert HA HVAC mode to Actron HVAC mode."""
        mode_map = {
            HVACMode.AUTO: "AUTO",
            HVACMode.HEAT: "HEAT",
            HVACMode.COOL: "COOL",
            HVACMode.FAN_ONLY: "FAN",
            HVACMode.OFF: "OFF",
        }
        return mode_map.get(mode, "OFF")

    @property
    def device_info(self):
        """Return device information about this entity."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.device_id)},
            "name": self.name,
            "manufacturer": "ActronAir",
            "model": self.coordinator.data["main"]["model"],
            "sw_version": self.coordinator.data["main"]["firmware_version"],
        }

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        actron_fan_mode = self.coordinator.data["main"]["fan_mode"]
        return {
            "away_mode": self.coordinator.data["main"]["away_mode"],
            "quiet_mode": self.coordinator.data["main"]["quiet_mode"],
            "continuous_fan": "+CONT" in actron_fan_mode if actron_fan_mode else False,
            "base_fan_mode": actron_fan_mode.split("+")[0]
            if actron_fan_mode
            else "LOW",
        }


class ActronZoneClimate(ActronEntityBase, ClimateEntity):
    """Zone climate entity with enhanced control capabilities."""

    def __init__(self, coordinator: ActronDataCoordinator, zone_id: str) -> None:
        """Initialize the zone climate entity."""
        zone_name = coordinator.data["zones"][zone_id]["name"]
        super().__init__(coordinator, "climate", f"Zone {zone_name}")

        self.zone_id = zone_id

        # Load capabilities from coordinator data
        zone_data = coordinator.data["zones"][zone_id]
        capabilities = zone_data.get("capabilities", {})

        self._can_operate = capabilities.get("can_operate", False)
        self._exists = capabilities.get("exists", False)
        self._has_temp_control = capabilities.get("has_temp_control", False)
        self._has_separate_targets = capabilities.get("has_separate_targets", False)

        if not self._has_temp_control:
            _LOGGER.debug(
                "Zone %s (%s) does not support individual temperature control",
                zone_id,
                coordinator.data["zones"][zone_id]["name"],
            )

        # Set up basic attributes
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_hvac_modes = [
            HVACMode.OFF,
            HVACMode.COOL,
            HVACMode.HEAT,
            HVACMode.AUTO,
        ]
        self._attr_min_temp = MIN_TEMP
        self._attr_max_temp = MAX_TEMP

        # Initialize hvac_mode based on zone state
        self._attr_hvac_mode = (
            HVACMode.OFF
            if not self.coordinator.data["zones"][zone_id]["is_enabled"]
            else self._actron_to_ha_hvac_mode(self.coordinator.data["main"]["mode"])
        )

        # Set up features based on capabilities
        features = ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF

        if self._has_temp_control:
            features |= ClimateEntityFeature.TARGET_TEMPERATURE
            if self._has_separate_targets:
                features |= ClimateEntityFeature.TARGET_TEMPERATURE_RANGE

        self._attr_supported_features = features

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            super().available
            and self.coordinator.enable_zone_control
            and self._exists
            and self._can_operate
            and self.coordinator.data["zones"].get(self.zone_id) is not None
        )

    @property
    def hvac_mode(self) -> HVACMode:
        """Return hvac operation ie. heat, cool mode."""
        # Return OFF if zone is disabled
        if not self.coordinator.data["zones"][self.zone_id]["is_enabled"]:
            return HVACMode.OFF

        # Return OFF if main system is off (even if zone is enabled)
        if not self.coordinator.data["main"]["is_on"]:
            return HVACMode.OFF

        # Otherwise use main unit's mode
        mode = self.coordinator.data["main"]["mode"]
        return self._actron_to_ha_hvac_mode(mode)

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self.coordinator.data["zones"][self.zone_id]["temp"]

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        if not self._has_temp_control:
            return None

        zone_data = self.coordinator.data["zones"][self.zone_id]
        main_mode = self.coordinator.data["main"]["mode"]

        try:
            if self._has_separate_targets:
                if main_mode == "COOL":
                    return zone_data["temp_setpoint_cool"]
                if main_mode == "HEAT":
                    return zone_data["temp_setpoint_heat"]
                if main_mode == "AUTO":
                    # In auto mode, return based on current compressor state
                    compressor_state = self.coordinator.data["main"]["compressor_state"]
                    if compressor_state == "COOL":
                        return zone_data["temp_setpoint_cool"]
                    if compressor_state == "HEAT":
                        return zone_data["temp_setpoint_heat"]
            else:
                # Single target mode
                return zone_data.get("temp_setpoint_heat")  # Default to heat setpoint

            return None

        except (KeyError, TypeError, ValueError) as err:
            _LOGGER.debug(
                "Error getting target temperature for zone %s: %s", self.zone_id, err
            )
            return None

    @property
    def target_temperature_high(self) -> float | None:
        """Return the high target temperature."""
        if not (self._has_temp_control and self._has_separate_targets):
            return None

        return self.coordinator.data["zones"][self.zone_id]["temp_setpoint_cool"]

    @property
    def target_temperature_low(self) -> float | None:
        """Return the low target temperature."""
        if not (self._has_temp_control and self._has_separate_targets):
            return None

        return self.coordinator.data["zones"][self.zone_id]["temp_setpoint_heat"]

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        if not self.coordinator.enable_zone_control:
            _LOGGER.warning("Cannot set HVAC mode: Zone control is disabled")
            return

        try:
            if hvac_mode == HVACMode.OFF:
                await self.coordinator.set_zone_state(self.zone_id, False)
            else:
                await self.coordinator.set_zone_state(self.zone_id, True)
                actron_mode = self._ha_to_actron_hvac_mode(hvac_mode)
                await self.coordinator.set_climate_mode(actron_mode)

            self._attr_hvac_mode = hvac_mode
            self.async_write_ha_state()

        except Exception as err:
            _LOGGER.error("Failed to set HVAC mode for zone %s: %s", self.zone_id, err)
            raise

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        if not self._has_temp_control:
            _LOGGER.warning(
                "Zone %s does not support temperature control",
                self.coordinator.data["zones"][self.zone_id]["name"],
            )
            return

        if not self.coordinator.enable_zone_control:
            _LOGGER.warning("Cannot set temperature: Zone control is disabled")
            return

        try:
            zone_index = int(self.zone_id.split("_")[1]) - 1

            if self._has_separate_targets:
                # Handle separate heat/cool targets
                target_high = kwargs.get("target_temp_high")
                target_low = kwargs.get("target_temp_low")

                if target_high is not None or target_low is not None:
                    await self.coordinator.api.set_zone_temperature(
                        zone_index=zone_index,
                        target_cool=target_high,
                        target_heat=target_low,
                    )

                else:
                    # Handle single target when separate targets are supported
                    temperature = kwargs.get(ATTR_TEMPERATURE)
                    if temperature is not None:
                        await self.coordinator.api.set_zone_temperature(
                            zone_index=zone_index,
                            target_cool=temperature,
                            target_heat=temperature,
                        )

            else:
                # Handle single target
                temperature = kwargs.get(ATTR_TEMPERATURE)
                if temperature is not None:
                    if not MIN_TEMP <= temperature <= MAX_TEMP:
                        _LOGGER.warning(
                            "Requested temperature %s outside valid range", temperature
                        )
                        return

                    await self.coordinator.api.set_zone_temperature(
                        zone_index=zone_index, temperature=temperature
                    )

            await self.coordinator.async_request_refresh()

        except Exception as err:
            _LOGGER.error(
                "Failed to set temperature for zone %s: %s", self.zone_id, err
            )
            raise

    async def async_turn_on(self) -> None:
        """Turn the entity on."""
        if not self.coordinator.enable_zone_control:
            _LOGGER.warning("Cannot turn on: Zone control is disabled")
            return

        try:
            await self.coordinator.set_zone_state(self.zone_id, True)
            main_mode = self.coordinator.data["main"]["mode"]
            self._attr_hvac_mode = self._actron_to_ha_hvac_mode(main_mode)
            self.async_write_ha_state()
        except ConfigurationError as err:
            _LOGGER.warning(
                "Configuration issue turning on zone %s: %s", self.zone_id, err
            )
            # Don't re-raise configuration errors - just log and continue
        except ZoneError as err:
            _LOGGER.error(
                "Zone-specific error turning on zone %s: %s", self.zone_id, err
            )
            raise
        except ApiError as err:
            if err.is_temporary:
                _LOGGER.warning(
                    "Temporary API error turning on zone %s: %s", self.zone_id, err
                )
            else:
                _LOGGER.error("API error turning on zone %s: %s", self.zone_id, err)
                raise
        except Exception as err:
            _LOGGER.error(
                "Unexpected error turning on zone %s: %s",
                self.zone_id,
                err,
                exc_info=True,
            )
            raise

    async def async_turn_off(self) -> None:
        """Turn the entity off."""
        if not self.coordinator.enable_zone_control:
            _LOGGER.warning("Cannot turn off: Zone control is disabled")
            return

        try:
            await self.coordinator.set_zone_state(self.zone_id, False)
            self._attr_hvac_mode = HVACMode.OFF
            self.async_write_ha_state()
        except Exception as err:
            _LOGGER.error("Failed to turn off zone %s: %s", self.zone_id, err)
            raise

    def _actron_to_ha_hvac_mode(self, mode: str) -> HVACMode:
        """Convert Actron HVAC mode to HA HVAC mode."""
        mode_map = {
            "AUTO": HVACMode.AUTO,
            "HEAT": HVACMode.HEAT,
            "COOL": HVACMode.COOL,
            "FAN": HVACMode.FAN_ONLY,
            "OFF": HVACMode.OFF,
        }
        return mode_map.get(mode.upper(), HVACMode.OFF)

    def _ha_to_actron_hvac_mode(self, mode: HVACMode) -> str:
        """Convert HA HVAC mode to Actron HVAC mode."""
        mode_map = {
            HVACMode.AUTO: "AUTO",
            HVACMode.HEAT: "HEAT",
            HVACMode.COOL: "COOL",
            HVACMode.FAN_ONLY: "FAN",
            HVACMode.OFF: "OFF",
        }
        return mode_map.get(mode, "OFF")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return zone specific attributes."""
        zone_data = self.coordinator.data["zones"][self.zone_id]
        data = {
            "zone_name": zone_data["name"],
            "supports_temperature_control": self._has_temp_control,
            "supports_separate_targets": self._has_separate_targets,
            "current_humidity": zone_data["humidity"],
        }

        # Add capability information if relevant
        if capabilities := zone_data.get("capabilities"):
            data["capabilities"] = capabilities

        return data
