"""Tests for the ActronAir Neo coordinator."""

from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.actronair_neo.api import (
    ActronApi,
    ApiError,
    AuthenticationError,
    DeviceOfflineError,
    RateLimitError,
)
from custom_components.actronair_neo.coordinator import ActronDataCoordinator


class TestActronDataCoordinator:
    """Test the ActronDataCoordinator class."""

    @pytest.mark.asyncio
    async def test_coordinator_initialization(
        self, hass: HomeAssistant, mock_api: ActronApi
    ) -> None:
        """Test coordinator initialization."""
        coordinator = ActronDataCoordinator(
            hass=hass,
            api=mock_api,
            device_id="TEST123456",
            update_interval=60,
            enable_zone_control=True,
        )

        assert coordinator.api == mock_api
        assert coordinator.device_id == "TEST123456"
        assert coordinator.enable_zone_control is True
        assert coordinator.last_data is None
        assert coordinator._continuous_fan is False

    @pytest.mark.asyncio
    async def test_successful_data_update(
        self,
        hass: HomeAssistant,
        mock_api: ActronApi,
        mock_api_response: dict[str, Any],
    ) -> None:
        """Test successful data update."""
        coordinator = ActronDataCoordinator(
            hass=hass,
            api=mock_api,
            device_id="TEST123456",
            update_interval=60,
            enable_zone_control=True,
        )

        # Mock API response
        mock_api.get_ac_status = AsyncMock(return_value=mock_api_response)
        mock_api.is_api_healthy = MagicMock(return_value=True)
        mock_api.cleanup_expired_cache = AsyncMock()

        # Mock zone capabilities
        mock_api.get_zone_capabilities = MagicMock(
            return_value={
                "exists": True,
                "can_operate": True,
                "has_temp_control": True,
                "has_separate_targets": False,
                "target_temp_cool": 22.0,
                "target_temp_heat": 20.0,
                "peripheral_capabilities": None,
            }
        )

        # Perform update
        result = await coordinator._async_update_data()

        # Verify result structure
        assert "main" in result
        assert "zones" in result
        assert "raw_data" in result

        # Verify main data
        main_data = result["main"]
        assert main_data["is_on"] is True
        assert main_data["mode"] == "COOL"
        assert main_data["fan_mode"] == "AUTO"
        assert main_data["indoor_temp"] == 23.5
        assert main_data["indoor_humidity"] == 45

        # Verify zones data
        zones_data = result["zones"]
        assert "zone_1" in zones_data
        assert "zone_2" in zones_data

        zone_1 = zones_data["zone_1"]
        assert zone_1["name"] == "Living Room"
        assert zone_1["temp"] == 22.0
        assert zone_1["humidity"] == 40

        # Verify coordinator state
        assert coordinator.last_data == result

        # Verify API calls
        mock_api.get_ac_status.assert_called_once_with("TEST123456", use_cache=True)
        mock_api.cleanup_expired_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_api_unhealthy_fallback(
        self,
        hass: HomeAssistant,
        mock_api: ActronApi,
        mock_api_response: dict[str, Any],
    ) -> None:
        """Test fallback to cached data when API is unhealthy."""
        coordinator = ActronDataCoordinator(
            hass=hass,
            api=mock_api,
            device_id="TEST123456",
            update_interval=60,
            enable_zone_control=True,
        )

        # Set up cached data
        coordinator.last_data = {"cached": "data"}

        # Mock unhealthy API
        mock_api.is_api_healthy = MagicMock(return_value=False)

        # Perform update
        result = await coordinator._async_update_data()

        # Should return cached data
        assert result == {"cached": "data"}

        # Should not have called API
        mock_api.get_ac_status.assert_not_called()

    @pytest.mark.asyncio
    async def test_authentication_error_handling(
        self,
        hass: HomeAssistant,
        mock_api: ActronApi,
    ) -> None:
        """Test authentication error handling."""
        coordinator = ActronDataCoordinator(
            hass=hass,
            api=mock_api,
            device_id="TEST123456",
            update_interval=60,
            enable_zone_control=True,
        )

        # Mock authentication error
        mock_api.is_api_healthy = MagicMock(return_value=True)
        mock_api.get_ac_status = AsyncMock(
            side_effect=AuthenticationError("Auth failed")
        )
        mock_api.clear_all_caches = AsyncMock()

        # Should raise ConfigEntryAuthFailed
        with pytest.raises(ConfigEntryAuthFailed):
            await coordinator._async_update_data()

        # Should clear caches on auth failure
        mock_api.clear_all_caches.assert_called_once()

    @pytest.mark.asyncio
    async def test_api_error_with_cached_data(
        self,
        hass: HomeAssistant,
        mock_api: ActronApi,
    ) -> None:
        """Test API error handling with cached data fallback."""
        coordinator = ActronDataCoordinator(
            hass=hass,
            api=mock_api,
            device_id="TEST123456",
            update_interval=60,
            enable_zone_control=True,
        )

        # Set up cached data
        coordinator.last_data = {"cached": "data"}

        # Mock API error
        mock_api.is_api_healthy = MagicMock(return_value=True)
        mock_api.get_ac_status = AsyncMock(side_effect=ApiError("API failed"))

        # Should return cached data
        result = await coordinator._async_update_data()
        assert result == {"cached": "data"}

    @pytest.mark.asyncio
    async def test_api_error_without_cached_data(
        self,
        hass: HomeAssistant,
        mock_api: ActronApi,
    ) -> None:
        """Test API error handling without cached data."""
        coordinator = ActronDataCoordinator(
            hass=hass,
            api=mock_api,
            device_id="TEST123456",
            update_interval=60,
            enable_zone_control=True,
        )

        # No cached data
        coordinator.last_data = None

        # Mock API error
        mock_api.is_api_healthy = MagicMock(return_value=True)
        mock_api.get_ac_status = AsyncMock(side_effect=ApiError("API failed"))

        # Should raise UpdateFailed
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()

    @pytest.mark.asyncio
    async def test_data_parsing_methods(
        self,
        hass: HomeAssistant,
        mock_api: ActronApi,
        mock_api_response: dict[str, Any],
    ) -> None:
        """Test data parsing methods."""
        coordinator = ActronDataCoordinator(
            hass=hass,
            api=mock_api,
            device_id="TEST123456",
            update_interval=60,
            enable_zone_control=True,
        )

        # Mock zone capabilities
        mock_api.get_zone_capabilities = MagicMock(
            return_value={
                "exists": True,
                "can_operate": True,
                "has_temp_control": True,
                "has_separate_targets": False,
                "target_temp_cool": 22.0,
                "target_temp_heat": 20.0,
                "peripheral_capabilities": None,
            }
        )

        # Test data extraction
        last_known_state = mock_api_response["lastKnownState"]
        data_sections = coordinator._extract_data_sections(last_known_state)

        assert "user_aircon_settings" in data_sections
        assert "master_info" in data_sections
        assert "live_aircon" in data_sections
        assert "aircon_system" in data_sections
        assert "indoor_unit" in data_sections
        assert "alerts" in data_sections
        assert "remote_zone_info" in data_sections
        assert "peripherals" in data_sections

        # Test main data parsing
        main_data = await coordinator._parse_main_data(data_sections)

        assert main_data["is_on"] is True
        assert main_data["mode"] == "COOL"
        assert main_data["fan_mode"] == "AUTO"
        assert main_data["fan_continuous"] is False
        assert main_data["base_fan_mode"] == "AUTO"
        assert main_data["indoor_temp"] == 23.5
        assert main_data["indoor_humidity"] == 45
        assert main_data["compressor_state"] == "COOLING"
        assert main_data["away_mode"] is False
        assert main_data["quiet_mode"] is False
        assert main_data["filter_clean_required"] is False
        assert main_data["defrosting"] is False

        # Test zones data parsing
        zones_data = await coordinator._parse_zones_data(data_sections)

        assert "zone_1" in zones_data
        assert "zone_2" in zones_data

        zone_1 = zones_data["zone_1"]
        assert zone_1["name"] == "Living Room"
        assert zone_1["temp"] == 22.0
        assert zone_1["humidity"] == 40
        assert zone_1["is_enabled"] is True
        assert zone_1["battery_level"] == 85
        assert zone_1["signal_strength"] == 2

    @pytest.mark.asyncio
    async def test_cache_management_methods(
        self,
        hass: HomeAssistant,
        mock_api: ActronApi,
    ) -> None:
        """Test cache management methods."""
        coordinator = ActronDataCoordinator(
            hass=hass,
            api=mock_api,
            device_id="TEST123456",
            update_interval=60,
            enable_zone_control=True,
        )

        # Mock API methods
        mock_api.clear_all_caches = AsyncMock()
        mock_api._invalidate_status_cache = AsyncMock()
        mock_api.cleanup_expired_cache = AsyncMock()

        # Test force update
        with patch.object(
            coordinator, "async_refresh", new_callable=AsyncMock
        ) as mock_refresh:
            await coordinator.force_update()
            mock_api.clear_all_caches.assert_called_once()
            mock_refresh.assert_called_once()

        # Test cache invalidation
        await coordinator.invalidate_cache()
        mock_api._invalidate_status_cache.assert_called_once_with("TEST123456")

        # Test cache cleanup
        await coordinator.cleanup_expired_cache()
        mock_api.cleanup_expired_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_statistics(
        self,
        hass: HomeAssistant,
        mock_api: ActronApi,
    ) -> None:
        """Test cache statistics."""
        coordinator = ActronDataCoordinator(
            hass=hass,
            api=mock_api,
            device_id="TEST123456",
            update_interval=60,
            enable_zone_control=True,
        )

        # Mock API properties
        mock_api.is_api_healthy = MagicMock(return_value=True)
        mock_api.last_successful_request = datetime.now()
        mock_api.error_count = 0
        mock_api.cached_status = {"some": "data"}

        # Set coordinator data
        coordinator.last_data = {"coordinator": "data"}

        # Get cache stats
        stats = coordinator.get_cache_stats()

        assert stats["api_health"] is True
        assert stats["last_successful_request"] is not None
        assert stats["error_count"] == 0
        assert stats["has_cached_status"] is True
        assert stats["coordinator_has_data"] is True

    @pytest.mark.asyncio
    async def test_periodic_cache_cleanup(
        self,
        hass: HomeAssistant,
        mock_api: ActronApi,
    ) -> None:
        """Test periodic cache cleanup."""
        coordinator = ActronDataCoordinator(
            hass=hass,
            api=mock_api,
            device_id="TEST123456",
            update_interval=60,
            enable_zone_control=True,
        )

        # Mock API method
        mock_api.cleanup_expired_cache = AsyncMock()

        # First call should trigger cleanup
        await coordinator._maybe_cleanup_cache()
        mock_api.cleanup_expired_cache.assert_called_once()
        assert coordinator._last_cache_cleanup is not None

        # Reset mock
        mock_api.cleanup_expired_cache.reset_mock()

        # Second call immediately should not trigger cleanup
        await coordinator._maybe_cleanup_cache()
        mock_api.cleanup_expired_cache.assert_not_called()

        # Simulate time passage
        coordinator._last_cache_cleanup = datetime.now() - timedelta(seconds=301)

        # Should trigger cleanup again
        await coordinator._maybe_cleanup_cache()
        mock_api.cleanup_expired_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_zone_control_toggle(
        self,
        hass: HomeAssistant,
        mock_api: ActronApi,
    ) -> None:
        """Test zone control enable/disable."""
        coordinator = ActronDataCoordinator(
            hass=hass,
            api=mock_api,
            device_id="TEST123456",
            update_interval=60,
            enable_zone_control=True,
        )

        # Mock refresh method
        with patch.object(
            coordinator, "async_request_refresh", new_callable=AsyncMock
        ) as mock_refresh:
            # Test disabling zone control
            await coordinator.set_zone_control(False)
            assert coordinator.enable_zone_control is False
            mock_refresh.assert_called_once()

            # Reset mock
            mock_refresh.reset_mock()

            # Test enabling zone control
            await coordinator.set_zone_control(True)
            assert coordinator.enable_zone_control is True
            mock_refresh.assert_called_once()


class TestEnhancedCoordinatorErrorHandling:
    """Test enhanced error handling in coordinator."""

    @pytest.mark.asyncio
    async def test_rate_limit_error_handling(
        self,
        hass: HomeAssistant,
        mock_api: ActronApi,
    ) -> None:
        """Test rate limit error handling with cached data fallback."""
        coordinator = ActronDataCoordinator(
            hass=hass,
            api=mock_api,
            device_id="TEST123456",
            update_interval=60,
            enable_zone_control=True,
        )

        # Set up cached data
        coordinator.last_data = {"cached": "data"}

        # Mock rate limit error
        mock_api.is_api_healthy = MagicMock(return_value=True)
        mock_api.get_ac_status = AsyncMock(
            side_effect=RateLimitError("Rate limited", retry_after=60)
        )

        # Should return cached data
        result = await coordinator._async_update_data()
        assert result == {"cached": "data"}

    @pytest.mark.asyncio
    async def test_device_offline_error_handling(
        self,
        hass: HomeAssistant,
        mock_api: ActronApi,
    ) -> None:
        """Test device offline error handling."""
        coordinator = ActronDataCoordinator(
            hass=hass,
            api=mock_api,
            device_id="TEST123456",
            update_interval=60,
            enable_zone_control=True,
        )

        # Set up cached data
        coordinator.last_data = {"cached": "data"}

        # Mock device offline error
        mock_api.is_api_healthy = MagicMock(return_value=True)
        mock_api.get_ac_status = AsyncMock(
            side_effect=DeviceOfflineError("Device offline", "TEST123456")
        )

        # Should return cached data
        result = await coordinator._async_update_data()
        assert result == {"cached": "data"}

    @pytest.mark.asyncio
    async def test_temporary_api_error_handling(
        self,
        hass: HomeAssistant,
        mock_api: ActronApi,
    ) -> None:
        """Test temporary API error handling."""
        coordinator = ActronDataCoordinator(
            hass=hass,
            api=mock_api,
            device_id="TEST123456",
            update_interval=60,
            enable_zone_control=True,
        )

        # Set up cached data
        coordinator.last_data = {"cached": "data"}

        # Mock temporary API error
        mock_api.is_api_healthy = MagicMock(return_value=True)
        temp_error = ApiError("Server error", status_code=503)
        mock_api.get_ac_status = AsyncMock(side_effect=temp_error)

        # Should return cached data for temporary errors
        result = await coordinator._async_update_data()
        assert result == {"cached": "data"}

    @pytest.mark.asyncio
    async def test_client_error_handling(
        self,
        hass: HomeAssistant,
        mock_api: ActronApi,
    ) -> None:
        """Test client error handling."""
        coordinator = ActronDataCoordinator(
            hass=hass,
            api=mock_api,
            device_id="TEST123456",
            update_interval=60,
            enable_zone_control=True,
        )

        # Set up cached data
        coordinator.last_data = {"cached": "data"}

        # Mock client error
        mock_api.is_api_healthy = MagicMock(return_value=True)
        client_error = ApiError("Bad request", status_code=400)
        mock_api.get_ac_status = AsyncMock(side_effect=client_error)

        # Should return cached data for client errors too
        result = await coordinator._async_update_data()
        assert result == {"cached": "data"}
