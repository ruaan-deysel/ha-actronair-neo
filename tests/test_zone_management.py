"""Tests for zone management enhancements."""

from __future__ import annotations

from datetime import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.actronair_neo.coordinator import ActronDataCoordinator
from custom_components.actronair_neo.exceptions import ConfigurationError
from custom_components.actronair_neo.zone_presets import (
    ZonePreset,
    ZonePresetManager,
    ZoneSchedule,
)


class TestZonePreset:
    """Test zone preset functionality."""

    def test_zone_preset_creation(self) -> None:
        """Test zone preset creation and serialization."""
        zones = {
            "zone_1": {"enabled": True, "temp_cool": 22.0, "temp_heat": 20.0},
            "zone_2": {"enabled": False, "temp_cool": 24.0, "temp_heat": 18.0},
        }

        preset = ZonePreset("Test Preset", zones, "Test description")

        assert preset.name == "Test Preset"
        assert preset.zones == zones
        assert preset.description == "Test description"
        assert preset.created_at is not None

    def test_zone_preset_serialization(self) -> None:
        """Test zone preset to/from dict conversion."""
        zones = {"zone_1": {"enabled": True, "temp_cool": 22.0}}
        preset = ZonePreset("Test", zones)

        # Test to_dict
        data = preset.to_dict()
        assert data["name"] == "Test"
        assert data["zones"] == zones
        assert "created_at" in data

        # Test from_dict
        restored_preset = ZonePreset.from_dict(data)
        assert restored_preset.name == preset.name
        assert restored_preset.zones == preset.zones


class TestZoneSchedule:
    """Test zone schedule functionality."""

    def test_zone_schedule_creation(self) -> None:
        """Test zone schedule creation."""
        schedule = ZoneSchedule(
            "Morning",
            "comfort_preset",
            time(7, 0),
            time(9, 0),
            [0, 1, 2, 3, 4],  # Weekdays
        )

        assert schedule.name == "Morning"
        assert schedule.preset_name == "comfort_preset"
        assert schedule.time_start == time(7, 0)
        assert schedule.time_end == time(9, 0)
        assert schedule.days == [0, 1, 2, 3, 4]
        assert schedule.enabled is True

    def test_zone_schedule_serialization(self) -> None:
        """Test zone schedule to/from dict conversion."""
        schedule = ZoneSchedule("Test", "preset", time(8, 0), time(17, 0), [0, 1])

        # Test to_dict
        data = schedule.to_dict()
        assert data["name"] == "Test"
        assert data["preset_name"] == "preset"
        assert data["time_start"] == "08:00:00"
        assert data["time_end"] == "17:00:00"
        assert data["days"] == [0, 1]

        # Test from_dict
        restored_schedule = ZoneSchedule.from_dict(data)
        assert restored_schedule.name == schedule.name
        assert restored_schedule.time_start == schedule.time_start

    @patch("custom_components.actronair_neo.zone_presets.dt_util.now")
    def test_schedule_is_active_now(self, mock_now) -> None:
        """Test schedule active time checking."""
        # Mock current time: Tuesday 8:30 AM
        mock_now.return_value.time.return_value = time(8, 30)
        mock_now.return_value.weekday.return_value = 1  # Tuesday

        # Schedule for weekdays 8:00-17:00
        schedule = ZoneSchedule(
            "Work", "preset", time(8, 0), time(17, 0), [0, 1, 2, 3, 4]
        )

        assert schedule.is_active_now() is True

        # Test outside time range
        mock_now.return_value.time.return_value = time(18, 0)
        assert schedule.is_active_now() is False

        # Test wrong day
        mock_now.return_value.time.return_value = time(8, 30)
        mock_now.return_value.weekday.return_value = 5  # Saturday
        assert schedule.is_active_now() is False


class TestZonePresetManager:
    """Test zone preset manager functionality."""

    @pytest.mark.asyncio
    async def test_preset_manager_initialization(self) -> None:
        """Test preset manager initialization."""
        hass = MagicMock()
        manager = ZonePresetManager(hass, "TEST123")

        assert manager.hass is hass
        assert manager.device_id == "TEST123"
        assert len(manager._presets) == 0
        assert len(manager._schedules) == 0

    @pytest.mark.asyncio
    async def test_create_preset(self) -> None:
        """Test creating a zone preset."""
        manager = ZonePresetManager(MagicMock(), "TEST123")
        zones = {"zone_1": {"enabled": True, "temp_cool": 22.0}}

        with patch.object(manager, "async_save", new_callable=AsyncMock):
            await manager.async_create_preset("Test", zones, "Description")

        assert "Test" in manager._presets
        preset = manager._presets["Test"]
        assert preset.zones == zones
        assert preset.description == "Description"

    @pytest.mark.asyncio
    async def test_create_duplicate_preset(self) -> None:
        """Test creating duplicate preset raises error."""
        manager = ZonePresetManager(MagicMock(), "TEST123")
        zones = {"zone_1": {"enabled": True}}

        with patch.object(manager, "async_save", new_callable=AsyncMock):
            await manager.async_create_preset("Test", zones)

            with pytest.raises(ConfigurationError, match="already exists"):
                await manager.async_create_preset("Test", zones)

    @pytest.mark.asyncio
    async def test_delete_preset_with_schedules(self) -> None:
        """Test deleting preset removes associated schedules."""
        hass = MagicMock()
        manager = ZonePresetManager(hass, "TEST123")

        with patch.object(manager, "async_save", new_callable=AsyncMock):
            # Create preset and schedule
            await manager.async_create_preset("Test", {"zone_1": {"enabled": True}})
            await manager.async_create_schedule(
                "Morning", "Test", time(8, 0), time(17, 0), [0, 1]
            )

            assert "Test" in manager._presets
            assert "Morning" in manager._schedules

            # Delete preset
            await manager.async_delete_preset("Test")

            assert "Test" not in manager._presets
            assert "Morning" not in manager._schedules


class TestCoordinatorZoneManagement:
    """Test coordinator zone management integration."""

    @pytest.mark.asyncio
    async def test_create_preset_from_current(
        self,
        hass: HomeAssistant,
        mock_api,
    ) -> None:
        """Test creating preset from current zone state."""
        coordinator = ActronDataCoordinator(
            hass=hass,
            api=mock_api,
            device_id="TEST123",
            update_interval=60,
            enable_zone_control=True,
        )

        # Set up coordinator data
        coordinator.last_data = {
            "zones": {
                "zone_1": {
                    "is_enabled": True,
                    "temp_setpoint_cool": 22.0,
                    "temp_setpoint_heat": 20.0,
                }
            }
        }

        with patch.object(
            coordinator.zone_preset_manager,
            "async_create_preset",
            new_callable=AsyncMock,
        ) as mock_create:
            await coordinator.async_create_zone_preset_from_current(
                "Test", "Description"
            )

            mock_create.assert_called_once()
            args = mock_create.call_args[0]
            assert args[0] == "Test"  # name
            assert args[2] == "Description"  # description
            zones_config = args[1]
            assert zones_config["zone_1"]["enabled"] is True
            assert zones_config["zone_1"]["temp_cool"] == 22.0

    @pytest.mark.asyncio
    async def test_bulk_zone_operation(
        self,
        hass: HomeAssistant,
        mock_api,
    ) -> None:
        """Test bulk zone operations."""
        coordinator = ActronDataCoordinator(
            hass=hass,
            api=mock_api,
            device_id="TEST123",
            update_interval=60,
            enable_zone_control=True,
        )

        with (
            patch.object(
                coordinator, "set_zone_state", new_callable=AsyncMock
            ) as mock_set_state,
            patch.object(coordinator, "async_request_refresh", new_callable=AsyncMock),
        ):
            results = await coordinator.async_bulk_zone_operation(
                "enable", ["zone_1", "zone_2"]
            )

            assert len(results) == 2
            assert all(r["status"] == "success" for r in results)
            assert mock_set_state.call_count == 2

    @pytest.mark.asyncio
    async def test_bulk_zone_operation_disabled(
        self,
        hass: HomeAssistant,
        mock_api,
    ) -> None:
        """Test bulk zone operation with zone control disabled."""
        coordinator = ActronDataCoordinator(
            hass=hass,
            api=mock_api,
            device_id="TEST123",
            update_interval=60,
            enable_zone_control=False,  # Disabled
        )

        with pytest.raises(ConfigurationError, match="not enabled"):
            await coordinator.async_bulk_zone_operation("enable", ["zone_1"])
