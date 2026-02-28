"""Tests for the ActronAir Neo number platform."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.actronair_neo.number import ActronAfterHoursDurationNumber

from .conftest import MOCK_SERIAL, create_mock_coordinator


@pytest.fixture
def coordinator(mock_api, mock_status):
    """Create a coordinator."""
    return create_mock_coordinator(MagicMock(), mock_api, mock_status)


# ── After Hours Duration Number Tests ────────────────────────────


class TestAfterHoursDurationNumber:
    """Tests for the ActronAfterHoursDurationNumber entity."""

    def test_native_value(self, coordinator):
        """Test native value returns after hours duration."""
        entity = ActronAfterHoursDurationNumber(coordinator)
        assert entity.native_value == 120

    def test_unique_id(self, coordinator):
        """Test unique ID contains serial."""
        entity = ActronAfterHoursDurationNumber(coordinator)
        assert MOCK_SERIAL in entity.unique_id

    def test_min_max_step(self, coordinator):
        """Test entity min/max/step attributes."""
        entity = ActronAfterHoursDurationNumber(coordinator)
        assert entity.native_min_value == 30
        assert entity.native_max_value == 480
        assert entity.native_step == 30

    @pytest.mark.asyncio
    async def test_set_native_value(self, coordinator):
        """Test setting native value calls coordinator."""
        coordinator.set_after_hours_duration = AsyncMock()
        coordinator.async_request_refresh = AsyncMock()
        entity = ActronAfterHoursDurationNumber(coordinator)
        await entity.async_set_native_value(240.0)
        coordinator.set_after_hours_duration.assert_called_once_with(240)
