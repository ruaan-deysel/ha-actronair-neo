"""Tests for the ActronAir Neo constants."""

from custom_components.actronair_neo.const import (
    CONF_ENABLE_ZONE_CONTROL,
    CONF_SERIAL_NUMBER,
    DEFAULT_REFRESH_INTERVAL,
    DEVICE_MANUFACTURER,
    DOMAIN,
    MAX_ZONES,
    PLATFORMS,
    VALID_FAN_MODES,
)


class TestConstants:
    """Tests for integration constants."""

    def test_domain(self):
        """Test domain value."""
        assert DOMAIN == "actronair_neo"

    def test_manufacturer(self):
        """Test manufacturer value."""
        assert DEVICE_MANUFACTURER == "ActronAir"

    def test_default_refresh_interval(self):
        """Test default refresh interval."""
        assert DEFAULT_REFRESH_INTERVAL == 30

    def test_config_keys(self):
        """Test config key values."""
        assert CONF_SERIAL_NUMBER == "serial_number"
        assert CONF_ENABLE_ZONE_CONTROL == "enable_zone_control"


class TestFanModeConstants:
    """Tests for fan mode constants."""

    def test_valid_fan_modes(self):
        """Test valid fan modes set."""
        assert {"LOW", "MED", "HIGH", "AUTO"} == VALID_FAN_MODES


class TestPlatforms:
    """Tests for platform configuration."""

    def test_platforms_not_empty(self):
        """Test platforms list is not empty."""
        assert len(PLATFORMS) > 0

    def test_max_zones(self):
        """Test max zones value."""
        assert MAX_ZONES == 8
