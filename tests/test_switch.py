"""Tests for the ActronAir Neo switch platform."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.actronair_neo.switch import (
    ActronAfterHoursSwitch,
    ActronAwayModeSwitch,
    ActronContinuousFanSwitch,
    ActronQuietModeSwitch,
    ActronTurboModeSwitch,
    ActronZoneSwitch,
    async_setup_entry,
)

from .conftest import MOCK_SERIAL, create_mock_coordinator


@pytest.fixture
def coordinator(mock_api, mock_status):
    """Create a coordinator for testing."""
    return create_mock_coordinator(MagicMock(), mock_api, mock_status)


@pytest.fixture
def coordinator_zones(mock_api, mock_status):
    """Create a coordinator with zone control enabled."""
    return create_mock_coordinator(
        MagicMock(), mock_api, mock_status, enable_zone_control=True
    )


# ── Away Mode Switch Tests ──────────────────────────────────────


class TestAwayModeSwitch:
    """Tests for the ActronAwayModeSwitch entity."""

    def test_is_on_false(self, coordinator):
        """Test away mode switch when off."""
        switch = ActronAwayModeSwitch(coordinator)
        assert switch.is_on is False

    def test_is_on_true(self, coordinator, mock_status):
        """Test away mode switch when on."""
        mock_status["main"]["away_mode"] = True
        switch = ActronAwayModeSwitch(coordinator)
        assert switch.is_on is True

    def test_unique_id(self, coordinator):
        """Test unique ID generation."""
        switch = ActronAwayModeSwitch(coordinator)
        assert MOCK_SERIAL in switch.unique_id

    @pytest.mark.asyncio
    async def test_turn_on(self, coordinator):
        """Test turning on away mode."""
        switch = ActronAwayModeSwitch(coordinator)
        await switch.async_turn_on()
        coordinator.set_away_mode.assert_called_once_with(state=True)

    @pytest.mark.asyncio
    async def test_turn_off(self, coordinator):
        """Test turning off away mode."""
        switch = ActronAwayModeSwitch(coordinator)
        await switch.async_turn_off()
        coordinator.set_away_mode.assert_called_once_with(state=False)


# ── Quiet Mode Switch Tests ─────────────────────────────────────


class TestQuietModeSwitch:
    """Tests for the ActronQuietModeSwitch entity."""

    def test_is_on_false(self, coordinator):
        """Test quiet mode switch when off."""
        switch = ActronQuietModeSwitch(coordinator)
        assert switch.is_on is False

    def test_is_on_true(self, coordinator, mock_status):
        """Test quiet mode switch when on."""
        mock_status["main"]["quiet_mode"] = True
        switch = ActronQuietModeSwitch(coordinator)
        assert switch.is_on is True

    @pytest.mark.asyncio
    async def test_turn_on(self, coordinator):
        """Test turning on quiet mode."""
        switch = ActronQuietModeSwitch(coordinator)
        await switch.async_turn_on()
        coordinator.set_quiet_mode.assert_called_once_with(state=True)

    @pytest.mark.asyncio
    async def test_turn_off(self, coordinator):
        """Test turning off quiet mode."""
        switch = ActronQuietModeSwitch(coordinator)
        await switch.async_turn_off()
        coordinator.set_quiet_mode.assert_called_once_with(state=False)


# ── Continuous Fan Switch Tests ──────────────────────────────────


class TestContinuousFanSwitch:
    """Tests for the ActronContinuousFanSwitch entity."""

    def test_is_on_false(self, coordinator):
        """Test continuous fan switch when off."""
        switch = ActronContinuousFanSwitch(coordinator)
        assert switch.is_on is False

    def test_is_on_true(self, coordinator, mock_status):
        """Test continuous fan switch when on."""
        mock_status["main"]["fan_mode"] = "LOW+CONT"
        switch = ActronContinuousFanSwitch(coordinator)
        assert switch.is_on is True

    def test_extra_state_attributes(self, coordinator, mock_status):
        """Test extra state attributes include fan mode info."""
        mock_status["main"]["fan_mode"] = "MED+CONT"
        switch = ActronContinuousFanSwitch(coordinator)
        attrs = switch.extra_state_attributes
        assert attrs["base_fan_mode"] == "MED"
        assert attrs["fan_mode"] == "MED+CONT"

    @pytest.mark.asyncio
    async def test_turn_on(self, coordinator, mock_status):
        """Test turning on continuous fan."""
        mock_status["main"]["fan_mode"] = "LOW"
        switch = ActronContinuousFanSwitch(coordinator)
        await switch.async_turn_on()
        coordinator.set_fan_mode.assert_called_once_with("LOW", continuous=True)

    @pytest.mark.asyncio
    async def test_turn_off(self, coordinator, mock_status):
        """Test turning off continuous fan."""
        mock_status["main"]["fan_mode"] = "LOW+CONT"
        switch = ActronContinuousFanSwitch(coordinator)
        await switch.async_turn_off()
        coordinator.set_fan_mode.assert_called_once_with("LOW", continuous=False)

    @pytest.mark.asyncio
    async def test_turn_on_invalid_mode_fallbacks(self, coordinator, mock_status):
        """Test invalid current and base fan mode fallback to LOW."""
        mock_status["main"]["fan_mode"] = "BAD-MODE"
        mock_status["main"]["base_fan_mode"] = "INVALID"
        switch = ActronContinuousFanSwitch(coordinator)
        with patch(
            "custom_components.actronair_neo.switch.asyncio.sleep", new=AsyncMock()
        ):
            await switch.async_turn_on()
        coordinator.set_fan_mode.assert_called_once_with("LOW", continuous=True)

    @pytest.mark.asyncio
    async def test_turn_off_invalid_mode_fallbacks(self, coordinator, mock_status):
        """Test invalid current/base mode fallback during turn off."""
        mock_status["main"]["fan_mode"] = "UNKNOWN+CONT"
        mock_status["main"]["base_fan_mode"] = "INVALID"
        switch = ActronContinuousFanSwitch(coordinator)
        with patch(
            "custom_components.actronair_neo.switch.asyncio.sleep", new=AsyncMock()
        ):
            await switch.async_turn_off()
        coordinator.set_fan_mode.assert_called_once_with("LOW", continuous=False)


# ── Zone Switch Tests ────────────────────────────────────────────


class TestZoneSwitch:
    """Tests for the ActronZoneSwitch entity."""

    def test_is_on_enabled(self, coordinator_zones):
        """Test zone switch when zone is enabled."""
        switch = ActronZoneSwitch(coordinator_zones, "zone_1")
        assert switch.is_on is True

    def test_is_on_disabled(self, coordinator_zones, mock_status):
        """Test zone switch when zone is disabled."""
        mock_status["zones"]["zone_1"]["is_enabled"] = False
        switch = ActronZoneSwitch(coordinator_zones, "zone_1")
        assert switch.is_on is False

    def test_available_when_zone_present(self, coordinator_zones):
        """Zone switch is available while its zone exists in data."""
        coordinator_zones.last_update_success = True
        switch = ActronZoneSwitch(coordinator_zones, "zone_1")
        assert switch.available is True

    def test_unavailable_when_zone_missing(self, coordinator_zones, mock_status):
        """A dropped zone renders the switch unavailable instead of raising."""
        coordinator_zones.last_update_success = True
        switch = ActronZoneSwitch(coordinator_zones, "zone_1")
        # Simulate a transient/partial update that dropped the zone.
        mock_status["zones"].pop("zone_1")
        assert switch.available is False

    def test_unique_id(self, coordinator_zones):
        """Test unique ID includes serial and zone info."""
        switch = ActronZoneSwitch(coordinator_zones, "zone_1")
        assert MOCK_SERIAL in switch.unique_id

    @pytest.mark.asyncio
    async def test_turn_on(self, coordinator_zones):
        """Test enabling a zone."""
        switch = ActronZoneSwitch(coordinator_zones, "zone_1")
        await switch.async_turn_on()
        # zone_1 → zone_index = 0
        coordinator_zones.set_zone_state.assert_called_once_with(0, enable=True)

    @pytest.mark.asyncio
    async def test_turn_off(self, coordinator_zones):
        """Test disabling a zone."""
        switch = ActronZoneSwitch(coordinator_zones, "zone_1")
        await switch.async_turn_off()
        coordinator_zones.set_zone_state.assert_called_once_with(0, enable=False)

    def test_second_zone(self, coordinator_zones):
        """Test switch for second zone."""
        switch = ActronZoneSwitch(coordinator_zones, "zone_2")
        assert MOCK_SERIAL in switch.unique_id

    @pytest.mark.asyncio
    async def test_second_zone_index(self, coordinator_zones):
        """Test second zone maps to index 1."""
        switch = ActronZoneSwitch(coordinator_zones, "zone_2")
        await switch.async_turn_on()
        # zone_2 → zone_index = 1
        coordinator_zones.set_zone_state.assert_called_once_with(1, enable=True)


# ── Turbo Mode Switch Tests ─────────────────────────────────────


class TestTurboModeSwitch:
    def test_is_on_false(self, coordinator):
        switch = ActronTurboModeSwitch(coordinator)
        assert switch.is_on is False

    def test_is_on_true(self, coordinator, mock_status):
        mock_status["main"]["turbo_mode_enabled"] = True
        switch = ActronTurboModeSwitch(coordinator)
        assert switch.is_on is True

    @pytest.mark.asyncio
    async def test_turn_on(self, coordinator):
        coordinator.set_turbo_mode = AsyncMock()
        switch = ActronTurboModeSwitch(coordinator)
        await switch.async_turn_on()
        coordinator.set_turbo_mode.assert_called_once_with(state=True)

    @pytest.mark.asyncio
    async def test_turn_off(self, coordinator):
        coordinator.set_turbo_mode = AsyncMock()
        switch = ActronTurboModeSwitch(coordinator)
        await switch.async_turn_off()
        coordinator.set_turbo_mode.assert_called_once_with(state=False)


# ── After Hours Switch Tests ─────────────────────────────────────


class TestAfterHoursSwitch:
    def test_is_on_false(self, coordinator):
        switch = ActronAfterHoursSwitch(coordinator)
        assert switch.is_on is False

    def test_is_on_true(self, coordinator, mock_status):
        mock_status["main"]["after_hours_enabled"] = True
        switch = ActronAfterHoursSwitch(coordinator)
        assert switch.is_on is True

    def test_extra_state_attributes(self, coordinator, mock_status):
        mock_status["main"]["after_hours_duration"] = 60
        switch = ActronAfterHoursSwitch(coordinator)
        attrs = switch.extra_state_attributes
        assert attrs["duration_minutes"] == 60

    @pytest.mark.asyncio
    async def test_turn_on(self, coordinator):
        coordinator.set_after_hours = AsyncMock()
        switch = ActronAfterHoursSwitch(coordinator)
        await switch.async_turn_on()
        coordinator.set_after_hours.assert_called_once_with(enabled=True)

    @pytest.mark.asyncio
    async def test_turn_off(self, coordinator):
        coordinator.set_after_hours = AsyncMock()
        switch = ActronAfterHoursSwitch(coordinator)
        await switch.async_turn_off()
        coordinator.set_after_hours.assert_called_once_with(enabled=False)


# ── async_setup_entry Tests ──────────────────────────────────────


class TestAsyncSetupEntry:
    @pytest.mark.asyncio
    async def test_setup_creates_entities(self, coordinator, mock_status):
        mock_status["main"]["quiet_mode_supported"] = True
        mock_status["main"]["turbo_mode_supported"] = True
        mock_entry = MagicMock()
        mock_entry.runtime_data = coordinator
        added: list = []
        await async_setup_entry(MagicMock(), mock_entry, added.extend)
        # away + continuous_fan + after_hours + quiet + turbo + 2 zones = 7
        assert len(added) == 7

    @pytest.mark.asyncio
    async def test_setup_without_optional(self, coordinator, mock_status):
        mock_status["main"]["quiet_mode_supported"] = False
        mock_status["main"]["turbo_mode_supported"] = False
        mock_entry = MagicMock()
        mock_entry.runtime_data = coordinator
        added: list = []
        await async_setup_entry(MagicMock(), mock_entry, added.extend)
        # away + continuous_fan + after_hours + 2 zones = 5
        assert len(added) == 5
