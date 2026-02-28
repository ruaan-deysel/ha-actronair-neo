"""Tests for performance optimization features."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.actronair_neo.coordinator import ActronDataCoordinator

# ── Coordinator performance tests ────────────────────────────────


def _make_coordinator(
    hass: HomeAssistant, mock_api: MagicMock
) -> ActronDataCoordinator:
    """Create a coordinator for perf tests."""
    return ActronDataCoordinator(
        hass=hass,
        api=mock_api,
        device_id="TEST123",
        update_interval=60,
        enable_zone_control=True,
    )


class TestCoordinatorPerformanceOptimizations:
    """Test coordinator performance optimizations."""

    @pytest.mark.asyncio
    async def test_parsed_data_caching(self, hass: HomeAssistant, mock_api) -> None:
        """Test parsed data caching optimization."""
        coordinator = _make_coordinator(hass, mock_api)
        # Prevent _maybe_cleanup_memory from clearing cache due to 0% hit rate
        coordinator._last_memory_cleanup = datetime.now()

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

            result1 = await coordinator._parse_data_optimized(mock_response)
            assert mock_parse.call_count == 1
            assert coordinator._cache_miss_count == 1
            assert coordinator._cache_hit_count == 0

            result2 = await coordinator._parse_data_optimized(mock_response)
            assert mock_parse.call_count == 1  # cached
            assert coordinator._cache_miss_count == 1
            assert coordinator._cache_hit_count == 1

            assert result1 == result2

    @pytest.mark.asyncio
    async def test_cache_invalidation_on_data_change(
        self, hass: HomeAssistant, mock_api
    ) -> None:
        """Test cache invalidation when data changes."""
        coordinator = _make_coordinator(hass, mock_api)

        response1 = {"lastKnownState": {"UserAirconSettings": {"Mode": "Cool"}}}
        response2 = {"lastKnownState": {"UserAirconSettings": {"Mode": "Heat"}}}

        with patch.object(
            coordinator, "_parse_data", new_callable=AsyncMock
        ) as mock_parse:
            mock_parse.side_effect = [
                {"main": {"mode": "cool"}, "zones": {}},
                {"main": {"mode": "heat"}, "zones": {}},
            ]

            await coordinator._parse_data_optimized(response1)
            assert coordinator._cache_miss_count == 1

            await coordinator._parse_data_optimized(response2)
            assert coordinator._cache_miss_count == 2
            assert mock_parse.call_count == 2

    @pytest.mark.asyncio
    async def test_memory_cleanup_low_hit_rate(
        self, hass: HomeAssistant, mock_api
    ) -> None:
        """Test memory cleanup when cache hit rate is low."""
        coordinator = _make_coordinator(hass, mock_api)

        coordinator._cache_hit_count = 1
        coordinator._cache_miss_count = 10  # 9% hit rate
        coordinator._parsed_data_cache = {"test": "data"}
        coordinator._raw_data_hash = 12345

        await coordinator._maybe_cleanup_memory()

        assert coordinator._parsed_data_cache is None
        assert coordinator._raw_data_hash is None

    @pytest.mark.asyncio
    async def test_counter_reset_after_threshold(
        self, hass: HomeAssistant, mock_api
    ) -> None:
        """Test counter reset after reaching threshold."""
        coordinator = _make_coordinator(hass, mock_api)

        coordinator._cache_hit_count = 800
        coordinator._cache_miss_count = 300  # Total > 1000

        await coordinator._maybe_cleanup_memory()

        assert coordinator._cache_hit_count == 0
        assert coordinator._cache_miss_count == 0

    async def test_performance_stats_calculation(
        self, hass: HomeAssistant, mock_api
    ) -> None:
        """Test performance statistics calculation."""
        coordinator = _make_coordinator(hass, mock_api)

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
    async def test_memory_cleanup_timing(self, hass: HomeAssistant, mock_api) -> None:
        """Test memory cleanup timing logic."""
        coordinator = _make_coordinator(hass, mock_api)

        # Recent cleanup — should not trigger again
        coordinator._last_memory_cleanup = datetime.now() - timedelta(minutes=5)
        old_cache = {"test": "data"}
        coordinator._parsed_data_cache = old_cache
        coordinator._raw_data_hash = 99

        await coordinator._maybe_cleanup_memory()
        # Cache should be untouched (cleanup skipped)
        assert coordinator._parsed_data_cache is old_cache

        # Old cleanup — should trigger
        coordinator._last_memory_cleanup = datetime.now() - timedelta(minutes=15)
        coordinator._cache_hit_count = 1
        coordinator._cache_miss_count = 10  # low hit rate → clear cache

        await coordinator._maybe_cleanup_memory()
        assert coordinator._parsed_data_cache is None
