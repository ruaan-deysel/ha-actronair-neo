from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature
from homeassistant.components.climate.const import (
    HVACMode,
    HVACAction,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
    FAN_AUTO,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MIN_TEMP, MAX_TEMP
from .coordinator import ActronDataCoordinator

import logging

_LOGGER = logging.getLogger(__name__)

HVAC_MODES = [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT, HVACMode.FAN_ONLY, HVACMode.AUTO]
FAN_MODES = [FAN_LOW, FAN_MEDIUM, FAN_HIGH, FAN_AUTO]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up Actron Neo climate from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ActronClimate(coordinator)], True)

class ActronClimate(CoordinatorEntity, ClimateEntity):
    """Representation of an Actron Neo Climate device."""

    def __init__(self, coordinator: ActronDataCoordinator):
        """Initialize the climate device."""
        super().__init__(coordinator)
        self._attr_name = "ActronAir Neo"
        self._attr_unique_id = f"{coordinator.device_id}_climate"
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_hvac_modes = HVAC_MODES
        self._attr_fan_modes = FAN_MODES
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE 
            | ClimateEntityFeature.FAN_MODE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        )
        self._attr_min_temp = MIN_TEMP
        self._attr_max_temp = MAX_TEMP

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.data is not None

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self.coordinator.data['main'].get('indoor_temp')

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        if self.hvac_mode == HVACMode.COOL:
            return self.coordinator.data['main'].get('temp_setpoint_cool')
        elif self.hvac_mode == HVACMode.HEAT:
            return self.coordinator.data['main'].get('temp_setpoint_heat')
        elif self.hvac_mode == HVACMode.AUTO:
            return self.coordinator.data['main'].get('temp_setpoint_cool')  # Default to cooling setpoint in AUTO mode
        return None

    @property
    def hvac_mode(self) -> HVACMode:
        """Return hvac operation ie. heat, cool mode."""
        if not self.coordinator.data['main'].get('is_on'):
            return HVACMode.OFF
        mode = self.coordinator.data['main'].get('mode')
        return self._actron_to_ha_hvac_mode(mode)

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return the current running hvac operation."""
        if not self.coordinator.data['main'].get('is_on'):
            return HVACAction.OFF
        compressor_state = self.coordinator.data['main'].get('compressor_state', 'OFF')
        if compressor_state == 'COOL':
            return HVACAction.COOLING
        elif compressor_state == 'HEAT':
            return HVACAction.HEATING
        elif self.hvac_mode == HVACMode.FAN_ONLY:
            return HVACAction.FAN
        return HVACAction.IDLE

    @property
    def fan_mode(self) -> str | None:
        """Return the fan setting."""
        return self.coordinator.data['main'].get('fan_mode')

    @property
    def current_humidity(self) -> int | None:
        """Return the current humidity."""
        humidity = self.coordinator.data['main'].get('indoor_humidity')
        return round(humidity) if humidity is not None else None

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            "outdoor_temperature": self.coordinator.data['main'].get('outdoor_temp'),
        }

    async def async_set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        is_cooling = self.hvac_mode in [HVACMode.COOL, HVACMode.AUTO]
        try:
            command = self.coordinator.api.create_command("SET_TEMP", temp=temperature, is_cool=is_cooling)
            await self.coordinator.api.send_command(self.coordinator.device_id, command)
            await self.coordinator.async_request_refresh()
        except Exception as e:
            _LOGGER.error(f"Failed to set temperature: {e}")

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        try:
            if hvac_mode == HVACMode.OFF:
                command = self.coordinator.api.create_command("OFF")
            else:
                command = self.coordinator.api.create_command("ON")
                await self.coordinator.api.send_command(self.coordinator.device_id, command)
                command = self.coordinator.api.create_command("CLIMATE_MODE", mode=self._ha_to_actron_hvac_mode(hvac_mode))
            await self.coordinator.api.send_command(self.coordinator.device_id, command)
            await self.coordinator.async_request_refresh()
        except Exception as e:
            _LOGGER.error(f"Failed to set HVAC mode: {e}")

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        try:
            command = self.coordinator.api.create_command("FAN_MODE", mode=fan_mode)
            await self.coordinator.api.send_command(self.coordinator.device_id, command)
            await self.coordinator.async_request_refresh()
        except Exception as e:
            _LOGGER.error(f"Failed to set fan mode: {e}")

    async def async_turn_on(self) -> None:
        """Turn the entity on."""
        try:
            command = self.coordinator.api.create_command("ON")
            await self.coordinator.api.send_command(self.coordinator.device_id, command)
            await self.coordinator.async_request_refresh()
        except Exception as e:
            _LOGGER.error(f"Failed to turn on: {e}")

    async def async_turn_off(self) -> None:
        """Turn the entity off."""
        try:
            command = self.coordinator.api.create_command("OFF")
            await self.coordinator.api.send_command(self.coordinator.device_id, command)
            await self.coordinator.async_request_refresh()
        except Exception as e:
            _LOGGER.error(f"Failed to turn off: {e}")

    def _actron_to_ha_hvac_mode(self, mode: str | None) -> HVACMode:
        """Convert Actron HVAC mode to HA HVAC mode."""
        if mode is None:
            return HVACMode.OFF
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

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    async def async_update(self) -> None:
        """Update the entity."""
        await self.coordinator.async_request_refresh()

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()