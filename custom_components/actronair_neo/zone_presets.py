"""Zone preset management for ActronAir Neo integration."""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, time
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .api import ConfigurationError

_LOGGER = logging.getLogger(__name__)

class ZonePreset:
    """Represents a zone preset configuration."""

    def __init__(
        self,
        name: str,
        zones: dict[str, dict[str, Any]],
        description: str = "",
        created_at: datetime | None = None,
    ):
        """
        Initialize zone preset.
        
        Args:
            name: Preset name
            zones: Zone configurations {zone_id: {enabled: bool, temp_cool: float, temp_heat: float}}
            description: Optional description
            created_at: Creation timestamp

        """
        self.name = name
        self.zones = zones
        self.description = description
        self.created_at = created_at or dt_util.utcnow()

    def to_dict(self) -> dict[str, Any]:
        """Convert preset to dictionary."""
        return {
            "name": self.name,
            "zones": self.zones,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ZonePreset:
        """Create preset from dictionary."""
        created_at = None
        if data.get("created_at"):
            try:
                created_at = datetime.fromisoformat(data["created_at"])
            except ValueError:
                created_at = dt_util.utcnow()

        return cls(
            name=data["name"],
            zones=data["zones"],
            description=data.get("description", ""),
            created_at=created_at,
        )

class ZoneSchedule:
    """Represents a zone schedule entry."""

    def __init__(
        self,
        name: str,
        preset_name: str,
        time_start: time,
        time_end: time,
        days: list[int],  # 0=Monday, 6=Sunday
        enabled: bool = True,
    ):
        """
        Initialize zone schedule.
        
        Args:
            name: Schedule name
            preset_name: Name of preset to apply
            time_start: Start time
            time_end: End time
            days: List of weekdays (0=Monday, 6=Sunday)
            enabled: Whether schedule is active

        """
        self.name = name
        self.preset_name = preset_name
        self.time_start = time_start
        self.time_end = time_end
        self.days = days
        self.enabled = enabled

    def to_dict(self) -> dict[str, Any]:
        """Convert schedule to dictionary."""
        return {
            "name": self.name,
            "preset_name": self.preset_name,
            "time_start": self.time_start.isoformat(),
            "time_end": self.time_end.isoformat(),
            "days": self.days,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ZoneSchedule:
        """Create schedule from dictionary."""
        return cls(
            name=data["name"],
            preset_name=data["preset_name"],
            time_start=time.fromisoformat(data["time_start"]),
            time_end=time.fromisoformat(data["time_end"]),
            days=data["days"],
            enabled=data.get("enabled", True),
        )

    def is_active_now(self) -> bool:
        """Check if schedule is currently active."""
        if not self.enabled:
            return False

        now = dt_util.now().time()
        today = dt_util.now().weekday()

        # Check if today is in scheduled days
        if today not in self.days:
            return False

        # Handle schedules that cross midnight
        if self.time_start <= self.time_end:
            return self.time_start <= now <= self.time_end
        return now >= self.time_start or now <= self.time_end

class ZonePresetManager:
    """Manages zone presets and schedules."""

    def __init__(self, hass: HomeAssistant, device_id: str):
        """
        Initialize preset manager.
        
        Args:
            hass: Home Assistant instance
            device_id: Device identifier

        """
        self.hass = hass
        self.device_id = device_id
        self._presets: dict[str, ZonePreset] = {}
        self._schedules: dict[str, ZoneSchedule] = {}
        self._storage_file = os.path.join(
            hass.config.config_dir, f"actron_zone_presets_{device_id}.json"
        )

    async def async_load(self) -> None:
        """Load presets and schedules from storage."""
        try:
            if os.path.exists(self._storage_file):
                with open(self._storage_file) as f:
                    data = json.load(f)

                # Load presets
                for preset_data in data.get("presets", []):
                    preset = ZonePreset.from_dict(preset_data)
                    self._presets[preset.name] = preset

                # Load schedules
                for schedule_data in data.get("schedules", []):
                    schedule = ZoneSchedule.from_dict(schedule_data)
                    self._schedules[schedule.name] = schedule

                _LOGGER.debug(
                    "Loaded %d presets and %d schedules for device %s",
                    len(self._presets), len(self._schedules), self.device_id
                )
        except Exception as err:
            _LOGGER.error("Failed to load zone presets: %s", err)

    async def async_save(self) -> None:
        """Save presets and schedules to storage."""
        try:
            data = {
                "presets": [preset.to_dict() for preset in self._presets.values()],
                "schedules": [schedule.to_dict() for schedule in self._schedules.values()],
            }

            with open(self._storage_file, "w") as f:
                json.dump(data, f, indent=2)

            _LOGGER.debug("Saved zone presets for device %s", self.device_id)
        except Exception as err:
            _LOGGER.error("Failed to save zone presets: %s", err)

    async def async_create_preset(
        self,
        name: str,
        zones: dict[str, dict[str, Any]],
        description: str = "",
    ) -> None:
        """
        Create a new zone preset.
        
        Args:
            name: Preset name
            zones: Zone configurations
            description: Optional description
            
        Raises:
            ConfigurationError: If preset name already exists

        """
        if name in self._presets:
            raise ConfigurationError(f"Preset '{name}' already exists")

        preset = ZonePreset(name, zones, description)
        self._presets[name] = preset
        await self.async_save()

        _LOGGER.info("Created zone preset '%s' with %d zones", name, len(zones))

    async def async_delete_preset(self, name: str) -> None:
        """
        Delete a zone preset.
        
        Args:
            name: Preset name
            
        Raises:
            ConfigurationError: If preset doesn't exist

        """
        if name not in self._presets:
            raise ConfigurationError(f"Preset '{name}' not found")

        # Remove any schedules using this preset
        schedules_to_remove = [
            schedule_name for schedule_name, schedule in self._schedules.items()
            if schedule.preset_name == name
        ]

        for schedule_name in schedules_to_remove:
            del self._schedules[schedule_name]

        del self._presets[name]
        await self.async_save()

        _LOGGER.info("Deleted zone preset '%s'", name)

    def get_preset(self, name: str) -> ZonePreset | None:
        """Get a zone preset by name."""
        return self._presets.get(name)

    def get_all_presets(self) -> dict[str, ZonePreset]:
        """Get all zone presets."""
        return self._presets.copy()

    async def async_create_schedule(
        self,
        name: str,
        preset_name: str,
        time_start: time,
        time_end: time,
        days: list[int],
        enabled: bool = True,
    ) -> None:
        """
        Create a new zone schedule.
        
        Args:
            name: Schedule name
            preset_name: Name of preset to apply
            time_start: Start time
            time_end: End time
            days: List of weekdays
            enabled: Whether schedule is active
            
        Raises:
            ConfigurationError: If schedule name exists or preset not found

        """
        if name in self._schedules:
            raise ConfigurationError(f"Schedule '{name}' already exists")

        if preset_name not in self._presets:
            raise ConfigurationError(f"Preset '{preset_name}' not found")

        schedule = ZoneSchedule(name, preset_name, time_start, time_end, days, enabled)
        self._schedules[name] = schedule
        await self.async_save()

        _LOGGER.info("Created zone schedule '%s' for preset '%s'", name, preset_name)

    def get_active_schedules(self) -> list[ZoneSchedule]:
        """Get currently active schedules."""
        return [
            schedule for schedule in self._schedules.values()
            if schedule.is_active_now()
        ]

    def get_all_schedules(self) -> dict[str, ZoneSchedule]:
        """Get all zone schedules."""
        return self._schedules.copy()
