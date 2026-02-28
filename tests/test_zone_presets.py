"""Tests for the ActronAir Neo zone presets."""

from datetime import time
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.util import dt as dt_util

from custom_components.actronair_neo.exceptions import ConfigurationError
from custom_components.actronair_neo.zone_presets import (
    ZonePreset,
    ZonePresetManager,
    ZoneSchedule,
)

MOCK_SERIAL = "ABC12345"


@pytest.fixture
def mock_hass():
    """Create a mock hass instance for zone presets."""
    return MagicMock()


@pytest.fixture
def manager(mock_hass):
    """Create a ZonePresetManager."""
    return ZonePresetManager(mock_hass, MOCK_SERIAL)


class TestZonePreset:
    """Tests for the ZonePreset class."""

    def test_init(self):
        """Test preset initialization."""
        preset = ZonePreset(
            name="Test",
            zones={"0": {"enabled": True}},
            description="A test preset",
        )
        assert preset.name == "Test"
        assert preset.zones == {"0": {"enabled": True}}
        assert preset.description == "A test preset"

    def test_to_dict(self):
        """Test converting preset to dict."""
        preset = ZonePreset(
            name="Test",
            zones={"0": {"enabled": True}},
            description="desc",
        )
        result = preset.to_dict()
        assert result["name"] == "Test"
        assert result["zones"] == {"0": {"enabled": True}}
        assert result["description"] == "desc"
        assert "created_at" in result

    def test_from_dict(self):
        """Test creating preset from dict."""
        data = {
            "name": "Test",
            "zones": {"0": {"enabled": True}},
            "description": "desc",
        }
        preset = ZonePreset.from_dict(data)
        assert preset.name == "Test"
        assert preset.zones == {"0": {"enabled": True}}
        assert preset.description == "desc"

    def test_from_dict_defaults(self):
        """Test creating preset from dict with defaults."""
        data = {"name": "Test", "zones": {}}
        preset = ZonePreset.from_dict(data)
        assert preset.zones == {}
        assert preset.description == ""

    def test_from_dict_roundtrip(self):
        """Test dict roundtrip (to_dict → from_dict)."""
        original = ZonePreset("RT", {"1": {"enabled": False}}, "round trip")
        rebuilt = ZonePreset.from_dict(original.to_dict())
        assert rebuilt.name == original.name
        assert rebuilt.zones == original.zones
        assert rebuilt.description == original.description

    def test_from_dict_invalid_created_at(self):
        """Test invalid created_at falls back to current UTC."""
        preset = ZonePreset.from_dict(
            {"name": "BadDate", "zones": {}, "created_at": "not-a-date"}
        )
        assert preset.name == "BadDate"


class TestZonePresetManager:
    """Tests for the ZonePresetManager class."""

    def test_init(self, manager):
        """Test manager initialization."""
        assert manager._presets == {}
        assert manager.device_id == MOCK_SERIAL

    def test_get_preset_missing(self, manager):
        """Test getting a non-existent preset."""
        assert manager.get_preset("nonexistent") is None

    @pytest.mark.asyncio
    async def test_create_preset(self, manager):
        """Test creating a preset."""
        await manager.async_create_preset(
            name="Test",
            zones={"0": {"enabled": True}},
            description="test",
        )
        assert "Test" in manager._presets
        assert manager._presets["Test"].name == "Test"

    @pytest.mark.asyncio
    async def test_create_duplicate_preset_raises(self, manager):
        """Test creating a duplicate preset raises ConfigurationError."""
        await manager.async_create_preset("Test", {"0": {"enabled": True}})
        with pytest.raises(ConfigurationError, match="already exists"):
            await manager.async_create_preset("Test", {"0": {"enabled": True}})

    @pytest.mark.asyncio
    async def test_delete_preset(self, manager):
        """Test deleting a preset."""
        await manager.async_create_preset(
            name="Test",
            zones={"0": {"enabled": True}},
        )
        await manager.async_delete_preset("Test")
        assert "Test" not in manager._presets

    @pytest.mark.asyncio
    async def test_delete_preset_not_found(self, manager):
        """Test deleting a non-existent preset raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="not found"):
            await manager.async_delete_preset("nonexistent")

    @pytest.mark.asyncio
    async def test_get_all_presets(self, manager):
        """Test getting all presets."""
        await manager.async_create_preset("P1", {"0": {"enabled": True}})
        await manager.async_create_preset("P2", {"1": {"enabled": False}})
        result = manager.get_all_presets()
        assert len(result) == 2
        assert "P1" in result
        assert "P2" in result

    @pytest.mark.asyncio
    async def test_load_presets(self, manager):
        """Test loading presets from storage."""
        presets_data = {
            "presets": [
                {
                    "name": "TestPreset",
                    "zones": {"0": {"enabled": True}},
                    "description": "loaded",
                }
            ],
            "schedules": [
                {
                    "name": "Morning",
                    "preset_name": "TestPreset",
                    "time_start": "07:00:00",
                    "time_end": "08:00:00",
                    "days": [0],
                    "enabled": True,
                }
            ],
        }
        manager._store.async_load = AsyncMock(return_value=presets_data)

        await manager.async_load()
        assert "TestPreset" in manager._presets
        assert manager._presets["TestPreset"].description == "loaded"
        assert "Morning" in manager._schedules

    @pytest.mark.asyncio
    async def test_load_presets_no_file(self, manager):
        """Test loading when storage file doesn't exist."""
        manager._store.async_load = AsyncMock(return_value=None)
        await manager.async_load()
        assert manager._presets == {}

    @pytest.mark.asyncio
    async def test_load_presets_corrupt_file(self, manager):
        """Test loading when storage raises an error."""
        manager._store.async_load = AsyncMock(side_effect=Exception("corrupt"))
        await manager.async_load()
        assert manager._presets == {}

    @pytest.mark.asyncio
    async def test_save_presets(self, manager):
        """Test saving presets to storage."""
        manager._store.async_save = AsyncMock()
        manager._presets["Test"] = ZonePreset("Test", {"0": {"enabled": True}})
        await manager.async_save()

        manager._store.async_save.assert_called_once()
        saved_data = manager._store.async_save.call_args[0][0]
        assert "presets" in saved_data
        assert len(saved_data["presets"]) == 1
        assert saved_data["presets"][0]["name"] == "Test"

    @pytest.mark.asyncio
    async def test_save_presets_exception(self, manager):
        """Test save handles storage exceptions."""
        manager._store.async_save = AsyncMock(side_effect=Exception("disk"))
        manager._presets["Test"] = ZonePreset("Test", {"0": {"enabled": True}})
        await manager.async_save()

    def test_get_preset(self, manager):
        """Test getting a preset by name."""
        preset = ZonePreset("Test", {"0": {"enabled": True}})
        manager._presets["Test"] = preset
        assert manager.get_preset("Test") is preset

    @pytest.mark.asyncio
    async def test_delete_preset_removes_schedules(self, manager):
        """Test deleting a preset removes linked schedules."""
        manager._store.async_save = AsyncMock()
        await manager.async_create_preset("Sleep", {"0": {"enabled": True}})
        await manager.async_create_schedule(
            "Night",
            "Sleep",
            time(22, 0),
            time(6, 0),
            [0, 1, 2, 3, 4],
        )
        assert "Night" in manager.get_all_schedules()
        await manager.async_delete_preset("Sleep")
        assert "Night" not in manager.get_all_schedules()

    @pytest.mark.asyncio
    async def test_create_schedule_validation(self, manager):
        """Test schedule creation validation errors."""
        with pytest.raises(ConfigurationError, match="Preset 'Missing' not found"):
            await manager.async_create_schedule(
                "Sched",
                "Missing",
                time(10, 0),
                time(11, 0),
                [0],
            )

        await manager.async_create_preset("Work", {"0": {"enabled": True}})
        await manager.async_create_schedule(
            "Sched",
            "Work",
            time(10, 0),
            time(11, 0),
            [0],
        )
        with pytest.raises(ConfigurationError, match="already exists"):
            await manager.async_create_schedule(
                "Sched",
                "Work",
                time(10, 0),
                time(11, 0),
                [0],
            )


class TestZoneSchedule:
    """Tests for ZoneSchedule behavior."""

    def test_schedule_to_from_dict(self):
        schedule = ZoneSchedule(
            "Morning",
            "Home",
            time(7, 0),
            time(8, 0),
            [0, 1],
            enabled=True,
        )
        rebuilt = ZoneSchedule.from_dict(schedule.to_dict())
        assert rebuilt.name == "Morning"
        assert rebuilt.preset_name == "Home"

    def test_schedule_is_active_now_disabled(self):
        schedule = ZoneSchedule(
            "Disabled",
            "Home",
            time(7, 0),
            time(8, 0),
            [0],
            enabled=False,
        )
        assert schedule.is_active_now() is False

    def test_schedule_is_active_now_today_not_in_days(self):
        """Test schedule is inactive when today is not in configured days."""
        schedule = ZoneSchedule(
            "Weekday",
            "Home",
            time(0, 0),
            time(23, 59),
            [],
            enabled=True,
        )
        assert schedule.is_active_now() is False

    def test_get_active_schedules_filters(self, manager):
        """Test active schedule filtering path."""
        active = ZoneSchedule("A", "P", time(0, 0), time(23, 59), [0], enabled=True)
        inactive = ZoneSchedule("B", "P", time(0, 0), time(0, 1), [0], enabled=False)
        active.is_active_now = MagicMock(return_value=True)
        inactive.is_active_now = MagicMock(return_value=False)
        manager._schedules = {"A": active, "B": inactive}
        assert [s.name for s in manager.get_active_schedules()] == ["A"]

    def test_schedule_is_active_now_cross_midnight(self, monkeypatch):
        """Test cross-midnight schedule active branch."""
        schedule = ZoneSchedule(
            "Night",
            "Home",
            time(22, 0),
            time(6, 0),
            [0, 1, 2, 3, 4, 5, 6],
            enabled=True,
        )

        fake_now = MagicMock()
        fake_now.time.return_value = time(23, 0)
        fake_now.weekday.return_value = 0
        monkeypatch.setattr(dt_util, "now", lambda: fake_now)

        assert schedule.is_active_now() is True
