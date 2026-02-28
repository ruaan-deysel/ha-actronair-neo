"""Tests for the ActronAir Neo base entity classes."""

from unittest.mock import MagicMock

import pytest

from custom_components.actronair_neo.const import DEVICE_MANUFACTURER, DOMAIN
from custom_components.actronair_neo.entity import (
    ActronAirNeoEntity,
)

from .conftest import MOCK_SERIAL, create_mock_coordinator


@pytest.fixture
def coordinator(mock_api, mock_status):
    """Create a coordinator for testing."""
    return create_mock_coordinator(MagicMock(), mock_api, mock_status)


class TestActronAirNeoEntity:
    """Tests for the base entity class."""

    def test_has_entity_name(self, coordinator):
        """Test entity has entity name enabled."""
        entity = ActronAirNeoEntity(coordinator, "test")
        assert entity._attr_has_entity_name is True

    def test_unique_id(self, coordinator):
        """Test unique ID generation."""
        entity = ActronAirNeoEntity(coordinator, "temperature")
        assert entity._attr_unique_id == f"{MOCK_SERIAL}_temperature"

    def test_unique_id_with_suffix(self, coordinator):
        """Test unique ID with name suffix."""
        entity = ActronAirNeoEntity(coordinator, "zone", "Living Room")
        assert entity._attr_unique_id == f"{MOCK_SERIAL}_zone_living_room"

    def test_device_info(self, coordinator, mock_status):
        """Test device info is set correctly."""
        entity = ActronAirNeoEntity(coordinator, "test")
        device_info = entity.device_info
        assert device_info is not None
        assert (DOMAIN, MOCK_SERIAL) in device_info["identifiers"]
        assert device_info["manufacturer"] == DEVICE_MANUFACTURER
        assert device_info["name"] == "ActronAir Neo"

    def test_device_info_model(self, coordinator, mock_status):
        """Test device info model from coordinator data."""
        entity = ActronAirNeoEntity(coordinator, "test")
        device_info = entity.device_info
        assert device_info is not None
        assert device_info["model"] == "NEO-12"

    def test_device_info_sw_version(self, coordinator, mock_status):
        """Test device info firmware version."""
        entity = ActronAirNeoEntity(coordinator, "test")
        device_info = entity.device_info
        assert device_info is not None
        assert device_info["sw_version"] == "1.2.3"

    def test_device_info_no_data(self, coordinator):
        """Test device info when coordinator data is None."""
        coordinator.data = None
        entity = ActronAirNeoEntity(coordinator, "test")
        assert entity.device_info is None

    def test_diagnostic_entity_category(self, coordinator):
        """Test diagnostic entity gets correct category."""
        entity = ActronAirNeoEntity(coordinator, "diag", is_diagnostic=True)
        assert entity._attr_entity_category is not None
