"""Tests for zone management enhancements."""

from datetime import datetime, time
from unittest.mock import AsyncMock, patch

import pytest
from custom_components.actronair_neo.zone_analytics import (
    ZoneAnalyticsManager,
    ZoneUsageStats,
)
from homeassistant.core import HomeAssistant

from custom_components.actronair_neo.api import (
    ActronApi,
    ConfigurationError,
)
from custom_components.actronair_neo.coordinator import ActronDataCoordinator
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
    async def test_preset_manager_initialization(self, hass: HomeAssistant) -> None:
        """Test preset manager initialization."""
        manager = ZonePresetManager(hass, "TEST123")

        assert manager.hass == hass
        assert manager.device_id == "TEST123"
        assert len(manager._presets) == 0
        assert len(manager._schedules) == 0

    @pytest.mark.asyncio
    async def test_create_preset(self, hass: HomeAssistant) -> None:
        """Test creating a zone preset."""
        manager = ZonePresetManager(hass, "TEST123")
        zones = {"zone_1": {"enabled": True, "temp_cool": 22.0}}

        with patch.object(manager, "async_save", new_callable=AsyncMock):
            await manager.async_create_preset("Test", zones, "Description")

        assert "Test" in manager._presets
        preset = manager._presets["Test"]
        assert preset.zones == zones
        assert preset.description == "Description"

    @pytest.mark.asyncio
    async def test_create_duplicate_preset(self, hass: HomeAssistant) -> None:
        """Test creating duplicate preset raises error."""
        manager = ZonePresetManager(hass, "TEST123")
        zones = {"zone_1": {"enabled": True}}

        with patch.object(manager, "async_save", new_callable=AsyncMock):
            await manager.async_create_preset("Test", zones)

            with pytest.raises(ConfigurationError, match="already exists"):
                await manager.async_create_preset("Test", zones)

    @pytest.mark.asyncio
    async def test_delete_preset_with_schedules(self, hass: HomeAssistant) -> None:
        """Test deleting preset removes associated schedules."""
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


class TestZoneUsageStats:
    """Test zone usage statistics."""

    def test_zone_stats_initialization(self) -> None:
        """Test zone stats initialization."""
        stats = ZoneUsageStats("zone_1")

        assert stats.zone_id == "zone_1"
        assert stats.total_runtime_hours == 0.0
        assert len(stats.daily_runtime_hours) == 0
        assert stats.setpoint_changes == 0
        assert stats.on_off_cycles == 0

    def test_record_temperature(self) -> None:
        """Test temperature recording."""
        stats = ZoneUsageStats("zone_1")

        stats.record_temperature(22.5, 22.0)

        assert len(stats.temperature_history) == 1
        reading = stats.temperature_history[0]
        assert reading["temperature"] == 22.5
        assert reading["setpoint"] == 22.0
        assert reading["variance"] == 0.5

    def test_record_state_change(self) -> None:
        """Test state change recording."""
        stats = ZoneUsageStats("zone_1")

        # Turn on
        stats.record_state_change(True)
        assert stats.on_off_cycles == 1

        # Turn off after 1 hour
        from datetime import timedelta

        later_time = datetime.now() + timedelta(hours=1)
        stats.record_state_change(False, later_time)

        assert stats.on_off_cycles == 2
        assert stats.total_runtime_hours == 1.0

    def test_efficiency_score_calculation(self) -> None:
        """Test efficiency score calculation."""
        stats = ZoneUsageStats("zone_1")

        # Add some temperature readings with low variance
        for i in range(10):
            stats.record_temperature(22.0 + (i % 2) * 0.1, 22.0)

        score = stats.calculate_efficiency_score()
        assert 80 <= score <= 100  # Should be high efficiency

        # Add readings with high variance
        for i in range(10):
            stats.record_temperature(22.0 + i * 2, 22.0)

        score = stats.calculate_efficiency_score()
        assert score < 50  # Should be lower efficiency


class TestZoneAnalyticsManager:
    """Test zone analytics manager."""

    @pytest.mark.asyncio
    async def test_analytics_manager_initialization(self, hass: HomeAssistant) -> None:
        """Test analytics manager initialization."""
        manager = ZoneAnalyticsManager(hass, "TEST123")

        assert manager.hass == hass
        assert manager.device_id == "TEST123"
        assert len(manager._zone_stats) == 0

    @pytest.mark.asyncio
    async def test_record_zone_data(self, hass: HomeAssistant) -> None:
        """Test recording zone data for analytics."""
        manager = ZoneAnalyticsManager(hass, "TEST123")

        await manager.async_record_zone_data("zone_1", 22.5, 22.0, True)

        assert "zone_1" in manager._zone_stats
        stats = manager._zone_stats["zone_1"]
        assert len(stats.temperature_history) == 1
        assert stats.last_state_change is not None

    @pytest.mark.asyncio
    async def test_system_summary(self, hass: HomeAssistant) -> None:
        """Test system analytics summary."""
        manager = ZoneAnalyticsManager(hass, "TEST123")

        # Add some data
        await manager.async_record_zone_data("zone_1", 22.0, 22.0, True)
        await manager.async_record_zone_data("zone_2", 24.0, 24.0, False)

        summary = manager.get_system_summary()

        assert summary["status"] == "ok"
        assert summary["total_zones"] == 2
        assert "most_used_zone" in summary
        assert "least_used_zone" in summary


class TestCoordinatorZoneManagement:
    """Test coordinator zone management integration."""

    @pytest.mark.asyncio
    async def test_create_preset_from_current(
        self,
        hass: HomeAssistant,
        mock_api: ActronApi,
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
        mock_api: ActronApi,
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
        mock_api: ActronApi,
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
