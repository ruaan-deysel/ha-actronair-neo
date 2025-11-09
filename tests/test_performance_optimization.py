"""Tests for performance optimization features."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.actronair_neo.api import ActronApi
from custom_components.actronair_neo.base_entity import ActronEntityBase
from custom_components.actronair_neo.coordinator import ActronDataCoordinator


class TestActronEntityBaseOptimizations:
    """Test base entity performance optimizations."""

    def test_state_hash_calculation(self) -> None:
        """Test state hash calculation for change detection."""
        coordinator = MagicMock()
        coordinator.device_id = "TEST123"

        entity = ActronEntityBase(coordinator, "test", "Test Entity")

        # Test simple values
        hash1 = entity._calculate_state_hash("test_value")
        hash2 = entity._calculate_state_hash("test_value")
        hash3 = entity._calculate_state_hash("different_value")

        assert hash1 == hash2
        assert hash1 != hash3

    def test_state_change_detection(self) -> None:
        """Test state change detection optimization."""
        coordinator = MagicMock()
        coordinator.device_id = "TEST123"

        entity = ActronEntityBase(coordinator, "test", "Test Entity")

        # First call should detect change
        assert entity._has_state_changed("initial_state") is True

        # Same state should not detect change
        assert entity._has_state_changed("initial_state") is False

        # Different state should detect change
        assert entity._has_state_changed("new_state") is True

    def test_attributes_change_detection(self) -> None:
        """Test attributes change detection optimization."""
        coordinator = MagicMock()
        coordinator.device_id = "TEST123"

        entity = ActronEntityBase(coordinator, "test", "Test Entity")

        attrs1 = {"key1": "value1", "key2": "value2"}
        attrs2 = {"key1": "value1", "key2": "value2"}
        attrs3 = {"key1": "value1", "key2": "different"}

        # First call should detect change
        assert entity._has_attributes_changed(attrs1) is True

        # Same attributes should not detect change
        assert entity._has_attributes_changed(attrs2) is False

        # Different attributes should detect change
        assert entity._has_attributes_changed(attrs3) is True

    def test_should_update_state_optimization(self) -> None:
        """Test should_update_state optimization logic."""
        coordinator = MagicMock()
        coordinator.device_id = "TEST123"

        entity = ActronEntityBase(coordinator, "test", "Test Entity")

        # Initial state should trigger update
        assert entity.should_update_state("state1", {"attr": "value1"}) is True

        # Same state and attributes should not trigger update
        assert entity.should_update_state("state1", {"attr": "value1"}) is False

        # Changed state should trigger update
        assert entity.should_update_state("state2", {"attr": "value1"}) is True

        # Changed attributes should trigger update
        assert entity.should_update_state("state2", {"attr": "value2"}) is True

    def test_complex_data_hashing(self) -> None:
        """Test hashing of complex data structures."""
        coordinator = MagicMock()
        coordinator.device_id = "TEST123"

        entity = ActronEntityBase(coordinator, "test", "Test Entity")

        # Test dict hashing
        dict1 = {"b": 2, "a": 1}
        dict2 = {"a": 1, "b": 2}  # Same content, different order
        dict3 = {"a": 1, "b": 3}  # Different content

        hash1 = entity._calculate_state_hash(dict1)
        hash2 = entity._calculate_state_hash(dict2)
        hash3 = entity._calculate_state_hash(dict3)

        assert hash1 == hash2  # Order shouldn't matter
        assert hash1 != hash3  # Content should matter

        # Test list hashing
        list1 = [1, 2, 3]
        list2 = [1, 2, 3]
        list3 = [1, 2, 4]

        hash1 = entity._calculate_state_hash(list1)
        hash2 = entity._calculate_state_hash(list2)
        hash3 = entity._calculate_state_hash(list3)

        assert hash1 == hash2
        assert hash1 != hash3


class TestCoordinatorPerformanceOptimizations:
    """Test coordinator performance optimizations."""

    @pytest.mark.asyncio
    async def test_parsed_data_caching(
        self,
        hass: HomeAssistant,
        mock_api: ActronApi,
    ) -> None:
        """Test parsed data caching optimization."""
        coordinator = ActronDataCoordinator(
            hass=hass,
            api=mock_api,
            device_id="TEST123",
            update_interval=60,
            enable_zone_control=True,
        )

        # Mock API response
        mock_response = {
            "lastKnownState": {
                "UserAirconSettings": {"Mode": "Cool"},
                "MasterInfo": {"LiveTemp_oC": 22.0},
                "RemoteZoneInfo": [],
            }
        }

        with patch.object(
            coordinator, "_parse_data", new_callable=AsyncMock
        ) as mock_parse:
            mock_parse.return_value = {"main": {"mode": "cool"}, "zones": {}}

            # First call should parse data
            result1 = await coordinator._parse_data_optimized(mock_response)
            assert mock_parse.call_count == 1
            assert coordinator._cache_miss_count == 1
            assert coordinator._cache_hit_count == 0

            # Second call with same data should use cache
            result2 = await coordinator._parse_data_optimized(mock_response)
            assert mock_parse.call_count == 1  # No additional calls
            assert coordinator._cache_miss_count == 1
            assert coordinator._cache_hit_count == 1

            assert result1 == result2

    @pytest.mark.asyncio
    async def test_cache_invalidation_on_data_change(
        self,
        hass: HomeAssistant,
        mock_api: ActronApi,
    ) -> None:
        """Test cache invalidation when data changes."""
        coordinator = ActronDataCoordinator(
            hass=hass,
            api=mock_api,
            device_id="TEST123",
            update_interval=60,
            enable_zone_control=True,
        )

        # Mock API responses
        response1 = {"lastKnownState": {"UserAirconSettings": {"Mode": "Cool"}}}
        response2 = {"lastKnownState": {"UserAirconSettings": {"Mode": "Heat"}}}

        with patch.object(
            coordinator, "_parse_data", new_callable=AsyncMock
        ) as mock_parse:
            mock_parse.side_effect = [
                {"main": {"mode": "cool"}, "zones": {}},
                {"main": {"mode": "heat"}, "zones": {}},
            ]

            # First call
            await coordinator._parse_data_optimized(response1)
            assert coordinator._cache_miss_count == 1

            # Second call with different data should parse again
            await coordinator._parse_data_optimized(response2)
            assert coordinator._cache_miss_count == 2
            assert mock_parse.call_count == 2

    @pytest.mark.asyncio
    async def test_memory_cleanup_low_hit_rate(
        self,
        hass: HomeAssistant,
        mock_api: ActronApi,
    ) -> None:
        """Test memory cleanup when cache hit rate is low."""
        coordinator = ActronDataCoordinator(
            hass=hass,
            api=mock_api,
            device_id="TEST123",
            update_interval=60,
            enable_zone_control=True,
        )

        # Simulate low cache hit rate
        coordinator._cache_hit_count = 1
        coordinator._cache_miss_count = 10  # 9% hit rate
        coordinator._parsed_data_cache = {"test": "data"}
        coordinator._raw_data_hash = 12345

        with patch.object(
            coordinator.zone_analytics_manager, "async_save", new_callable=AsyncMock
        ):
            await coordinator._maybe_cleanup_memory()

            # Cache should be cleared due to low hit rate
            assert coordinator._parsed_data_cache is None
            assert coordinator._raw_data_hash is None

    @pytest.mark.asyncio
    async def test_counter_reset_after_threshold(
        self,
        hass: HomeAssistant,
        mock_api: ActronApi,
    ) -> None:
        """Test counter reset after reaching threshold."""
        coordinator = ActronDataCoordinator(
            hass=hass,
            api=mock_api,
            device_id="TEST123",
            update_interval=60,
            enable_zone_control=True,
        )

        # Set counters above threshold
        coordinator._cache_hit_count = 800
        coordinator._cache_miss_count = 300  # Total > 1000

        with patch.object(
            coordinator.zone_analytics_manager, "async_save", new_callable=AsyncMock
        ):
            await coordinator._maybe_cleanup_memory()

            # Counters should be reset
            assert coordinator._cache_hit_count == 0
            assert coordinator._cache_miss_count == 0

    def test_performance_stats_calculation(
        self,
        hass: HomeAssistant,
        mock_api: ActronApi,
    ) -> None:
        """Test performance statistics calculation."""
        coordinator = ActronDataCoordinator(
            hass=hass,
            api=mock_api,
            device_id="TEST123",
            update_interval=60,
            enable_zone_control=True,
        )

        # Set test values
        coordinator._cache_hit_count = 80
        coordinator._cache_miss_count = 20
        coordinator._parsed_data_cache = {"test": "data"}

        stats = coordinator.get_performance_stats()

        assert stats["cache_hit_count"] == 80
        assert stats["cache_miss_count"] == 20
        assert stats["cache_hit_rate_percent"] == 80.0
        assert stats["total_parse_requests"] == 100
        assert stats["has_parsed_cache"] is True

    @pytest.mark.asyncio
    async def test_memory_cleanup_timing(
        self,
        hass: HomeAssistant,
        mock_api: ActronApi,
    ) -> None:
        """Test memory cleanup timing logic."""
        coordinator = ActronDataCoordinator(
            hass=hass,
            api=mock_api,
            device_id="TEST123",
            update_interval=60,
            enable_zone_control=True,
        )

        # Set last cleanup to recent time
        coordinator._last_memory_cleanup = datetime.now() - timedelta(minutes=5)

        with patch.object(
            coordinator.zone_analytics_manager, "async_save", new_callable=AsyncMock
        ) as mock_save:
            await coordinator._maybe_cleanup_memory()

            # Should not perform cleanup (too recent)
            mock_save.assert_not_called()

        # Set last cleanup to old time
        coordinator._last_memory_cleanup = datetime.now() - timedelta(minutes=15)

        with patch.object(
            coordinator.zone_analytics_manager, "async_save", new_callable=AsyncMock
        ) as mock_save:
            await coordinator._maybe_cleanup_memory()

            # Should perform cleanup
            mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_zone_analytics_integration(
        self,
        hass: HomeAssistant,
        mock_api: ActronApi,
    ) -> None:
        """Test zone analytics integration with caching."""
        coordinator = ActronDataCoordinator(
            hass=hass,
            api=mock_api,
            device_id="TEST123",
            update_interval=60,
            enable_zone_control=True,
        )

        # Mock zone data
        zones_data = {"zone_1": {"temp": 22.0, "setpoint": 22.0, "is_enabled": True}}

        with patch.object(
            coordinator, "_update_zone_analytics", new_callable=AsyncMock
        ) as mock_analytics:
            # Set up cached data
            coordinator._parsed_data_cache = {"zones": zones_data}
            coordinator._raw_data_hash = 12345

            # Call with same data (should use cache)
            mock_response = {"test": "data"}
            await coordinator._parse_data_optimized(mock_response)

            # Analytics should still be updated even with cached data
            mock_analytics.assert_called_once_with(zones_data)
