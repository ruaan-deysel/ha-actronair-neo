"""Tests for the ActronAir Neo API client."""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import ClientResponseError

from custom_components.actronair_neo.api import (
    ActronApi,
    ApiError,
    AuthenticationError,
    ConfigurationError,
    DeviceOfflineError,
    RateLimiter,
    RateLimitError,
    ResponseCache,
    ZoneError,
)
from custom_components.actronair_neo.const import MAX_RETRIES


class TestRateLimiter:
    """Test the RateLimiter class."""

    @pytest.mark.asyncio
    async def test_rate_limiter_basic_functionality(self) -> None:
        """Test basic rate limiter functionality."""
        limiter = RateLimiter(calls_per_minute=2)

        # Should allow first call immediately
        async with limiter:
            pass

        # Should allow second call immediately
        async with limiter:
            pass

        # Third call should be delayed (but we won't wait for it in test)
        assert len(limiter.call_times) == 2

    @pytest.mark.asyncio
    async def test_rate_limiter_acquire_release(self) -> None:
        """Test manual acquire/release."""
        limiter = RateLimiter(calls_per_minute=1)

        await limiter.acquire()
        assert len(limiter.call_times) == 1

        limiter.release()
        # Call times should still be recorded
        assert len(limiter.call_times) == 1


class TestResponseCache:
    """Test the ResponseCache class."""

    @pytest.mark.asyncio
    async def test_cache_set_and_get(self) -> None:
        """Test setting and getting cached values."""
        cache = ResponseCache(default_ttl=timedelta(seconds=30))

        await cache.set("test_key", {"data": "test_value"})
        result = await cache.get("test_key")

        assert result == {"data": "test_value"}

    @pytest.mark.asyncio
    async def test_cache_expiration(self) -> None:
        """Test cache expiration."""
        cache = ResponseCache(default_ttl=timedelta(milliseconds=1))

        await cache.set("test_key", {"data": "test_value"})

        # Wait for expiration
        await asyncio.sleep(0.002)

        result = await cache.get("test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_custom_ttl(self) -> None:
        """Test cache with custom TTL."""
        cache = ResponseCache(default_ttl=timedelta(seconds=30))

        await cache.set("test_key", {"data": "test_value"})

        # Get with very short TTL should return None after expiration
        await asyncio.sleep(0.001)
        result = await cache.get("test_key", ttl=timedelta(microseconds=1))
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_clear(self) -> None:
        """Test cache clearing."""
        cache = ResponseCache()

        await cache.set("key1", "value1")
        await cache.set("key2", "value2")

        await cache.clear()

        assert await cache.get("key1") is None
        assert await cache.get("key2") is None

    @pytest.mark.asyncio
    async def test_cache_cleanup_expired(self) -> None:
        """Test cleanup of expired entries."""
        cache = ResponseCache(default_ttl=timedelta(milliseconds=1))

        await cache.set("expired_key", "value")
        await cache.set("valid_key", "value")

        # Wait for first key to expire
        await asyncio.sleep(0.002)

        # Add another valid key after expiration
        await cache.set("another_valid_key", "value")

        await cache.cleanup_expired()

        # Only valid keys should remain
        assert await cache.get("expired_key") is None
        assert await cache.get("valid_key") is not None
        assert await cache.get("another_valid_key") is not None


class TestActronApi:
    """Test the ActronApi class."""

    @pytest.mark.asyncio
    async def test_api_initialization(self, mock_aiohttp_session) -> None:
        """Test API initialization."""
        api = ActronApi("test@example.com", "password", mock_aiohttp_session)

        assert api.username == "test@example.com"
        assert api.password == "password"
        assert api.session == mock_aiohttp_session
        assert api.access_token is None
        assert api.refresh_token_value is None

    @pytest.mark.asyncio
    async def test_api_health_tracking(self, mock_aiohttp_session) -> None:
        """Test API health tracking."""
        api = ActronApi("test@example.com", "password", mock_aiohttp_session)

        # Initially healthy
        assert api.is_api_healthy() is True

        # Simulate errors
        api.error_count = 6
        assert api.is_api_healthy() is False

        # Recent successful request should make it healthy again
        api.last_successful_request = datetime.now()
        assert api.is_api_healthy() is True

    @pytest.mark.asyncio
    async def test_get_ac_status_with_cache(
        self, mock_aiohttp_session, mock_api_response
    ) -> None:
        """Test getting AC status with caching."""
        api = ActronApi("test@example.com", "password", mock_aiohttp_session)
        api.access_token = "mock_token"
        api.token_expires_at = datetime.now() + timedelta(hours=1)

        # Mock successful response
        mock_response = MagicMock()
        mock_response.json = AsyncMock(return_value=mock_api_response)
        mock_response.status = 200
        mock_aiohttp_session.request.return_value.__aenter__.return_value = (
            mock_response
        )

        # First call should hit API
        result1 = await api.get_ac_status("TEST123456", use_cache=True)
        assert result1 == mock_api_response

        # Second call should use cache
        result2 = await api.get_ac_status("TEST123456", use_cache=True)
        assert result2 == mock_api_response

        # Should only have made one actual API call
        assert mock_aiohttp_session.request.call_count == 1

    @pytest.mark.asyncio
    async def test_get_ac_status_without_cache(
        self, mock_aiohttp_session, mock_api_response
    ) -> None:
        """Test getting AC status without caching."""
        api = ActronApi("test@example.com", "password", mock_aiohttp_session)
        api.access_token = "mock_token"
        api.token_expires_at = datetime.now() + timedelta(hours=1)

        # Mock successful response
        mock_response = MagicMock()
        mock_response.json = AsyncMock(return_value=mock_api_response)
        mock_response.status = 200
        mock_aiohttp_session.request.return_value.__aenter__.return_value = (
            mock_response
        )

        # Both calls should hit API
        await api.get_ac_status("TEST123456", use_cache=False)
        await api.get_ac_status("TEST123456", use_cache=False)

        # Should have made two API calls
        assert mock_aiohttp_session.request.call_count == 2

    @pytest.mark.asyncio
    async def test_send_command_invalidates_cache(self, mock_aiohttp_session) -> None:
        """Test that sending commands invalidates cache."""
        api = ActronApi("test@example.com", "password", mock_aiohttp_session)
        api.access_token = "mock_token"
        api.token_expires_at = datetime.now() + timedelta(hours=1)

        # Pre-populate cache
        await api.response_cache.set("ac_status_TEST123456", {"cached": "data"})

        # Mock successful command response
        mock_response = MagicMock()
        mock_response.json = AsyncMock(return_value={"success": True})
        mock_response.status = 200
        mock_aiohttp_session.request.return_value.__aenter__.return_value = (
            mock_response
        )

        # Send command
        command = {"UserAirconSettings": {"isOn": True}}
        await api.send_command("TEST123456", command)

        # Cache should be invalidated
        cached_data = await api.response_cache.get("ac_status_TEST123456")
        assert cached_data is None

    @pytest.mark.asyncio
    async def test_request_deduplication(
        self, mock_aiohttp_session, mock_api_response
    ) -> None:
        """Test request deduplication."""
        api = ActronApi("test@example.com", "password", mock_aiohttp_session)
        api.access_token = "mock_token"
        api.token_expires_at = datetime.now() + timedelta(hours=1)

        # Mock response with delay to simulate concurrent requests
        async def delayed_response(*args, **kwargs):
            await asyncio.sleep(0.01)
            mock_response = MagicMock()
            mock_response.json = AsyncMock(return_value=mock_api_response)
            mock_response.status = 200
            return mock_response

        mock_aiohttp_session.request.return_value.__aenter__ = delayed_response

        # Start multiple concurrent requests
        tasks = [
            api.get_ac_status("TEST123456", use_cache=False),
            api.get_ac_status("TEST123456", use_cache=False),
            api.get_ac_status("TEST123456", use_cache=False),
        ]

        results = await asyncio.gather(*tasks)

        # All should return the same result
        assert all(result == mock_api_response for result in results)

        # Should only have made one actual API call due to deduplication
        assert mock_aiohttp_session.request.call_count == 1

    @pytest.mark.asyncio
    async def test_api_error_handling(self, mock_aiohttp_session) -> None:
        """Test API error handling."""
        api = ActronApi("test@example.com", "password", mock_aiohttp_session)
        api.access_token = "mock_token"
        api.token_expires_at = datetime.now() + timedelta(hours=1)

        # Mock error response
        mock_aiohttp_session.request.side_effect = ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=500,
        )

        with pytest.raises(ApiError):
            await api.get_ac_status("TEST123456")

    @pytest.mark.asyncio
    async def test_authentication_error_handling(self, mock_aiohttp_session) -> None:
        """Test authentication error handling."""
        api = ActronApi("test@example.com", "password", mock_aiohttp_session)

        # Mock 401 response
        mock_aiohttp_session.request.side_effect = ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=401,
        )

        with pytest.raises(AuthenticationError):
            await api.get_ac_status("TEST123456")

    @pytest.mark.asyncio
    async def test_cache_management_methods(self, mock_aiohttp_session) -> None:
        """Test cache management methods."""
        api = ActronApi("test@example.com", "password", mock_aiohttp_session)

        # Pre-populate caches
        await api.response_cache.set("test_key", "test_value")
        api.cached_status = {"legacy": "data"}

        # Test clear all caches
        await api.clear_all_caches()

        assert await api.response_cache.get("test_key") is None
        assert api.cached_status is None

        # Test cache invalidation
        await api.response_cache.set("ac_status_TEST123456", "test_data")
        await api._invalidate_status_cache("TEST123456")

        assert await api.response_cache.get("ac_status_TEST123456") is None

    @pytest.mark.asyncio
    async def test_get_zone_statuses_with_cached_data(
        self, mock_aiohttp_session, mock_api_response
    ) -> None:
        """Test getting zone statuses with cached data."""
        api = ActronApi("test@example.com", "password", mock_aiohttp_session)
        api.actron_serial = "TEST123456"

        # Test with cached status
        result = await api.get_zone_statuses(cached_status=mock_api_response)
        expected = mock_api_response["lastKnownState"]["UserAirconSettings"][
            "EnabledZones"
        ]
        assert result == expected

        # Should not have made any API calls
        assert mock_aiohttp_session.request.call_count == 0


class TestEnhancedErrorHandling:
    """Test enhanced error handling features."""

    @pytest.mark.asyncio
    async def test_api_error_classification(self) -> None:
        """Test API error classification properties."""
        # Test temporary errors
        temp_error = ApiError("Server error", status_code=503)
        assert temp_error.is_temporary is True
        assert temp_error.is_client_error is False
        assert temp_error.is_server_error is True

        # Test client errors
        client_error = ApiError("Bad request", status_code=400)
        assert client_error.is_temporary is False
        assert client_error.is_client_error is True
        assert client_error.is_server_error is False

        # Test rate limit error
        rate_error = RateLimitError("Rate limited", retry_after=60)
        assert rate_error.is_temporary is True
        assert rate_error.status_code == 429
        assert rate_error.retry_after == 60

    @pytest.mark.asyncio
    async def test_device_offline_error(self) -> None:
        """Test device offline error handling."""
        error = DeviceOfflineError("Device is offline", device_id="TEST123")
        assert error.device_id == "TEST123"
        assert error.status_code == 503

    @pytest.mark.asyncio
    async def test_zone_error_handling(self) -> None:
        """Test zone-specific error handling."""
        zone_error = ZoneError("Zone not found", zone_id="zone_1", zone_index=0)
        assert zone_error.zone_id == "zone_1"
        assert zone_error.zone_index == 0

    @pytest.mark.asyncio
    async def test_configuration_error_handling(self) -> None:
        """Test configuration error handling."""
        config_error = ConfigurationError("Invalid config", config_key="username")
        assert config_error.config_key == "username"

    @pytest.mark.asyncio
    async def test_enhanced_api_error_responses(self, mock_aiohttp_session) -> None:
        """Test enhanced API error response handling."""
        api = ActronApi("test@example.com", "password", mock_aiohttp_session)
        api.access_token = "mock_token"
        api.token_expires_at = datetime.now() + timedelta(hours=1)

        # Test rate limit error
        mock_response = MagicMock()
        mock_response.status = 429
        mock_response.headers = {"Retry-After": "60"}
        mock_response.text = AsyncMock(return_value="Rate limit exceeded")
        mock_aiohttp_session.request.return_value.__aenter__.return_value = (
            mock_response
        )

        with pytest.raises(RateLimitError) as exc_info:
            await api.get_ac_status("TEST123456")

        assert exc_info.value.retry_after == 60
        assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_device_offline_detection(self, mock_aiohttp_session) -> None:
        """Test device offline detection."""
        api = ActronApi("test@example.com", "password", mock_aiohttp_session)
        api.access_token = "mock_token"
        api.token_expires_at = datetime.now() + timedelta(hours=1)
        api.actron_serial = "TEST123456"

        # Test service unavailable with device offline indication
        mock_response = MagicMock()
        mock_response.status = 503
        mock_response.text = AsyncMock(return_value="Device offline")
        mock_aiohttp_session.request.return_value.__aenter__.return_value = (
            mock_response
        )

        with pytest.raises(DeviceOfflineError) as exc_info:
            await api.get_ac_status("TEST123456")

        assert exc_info.value.device_id == "TEST123456"
        assert "offline" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_server_error_retry_logic(self, mock_aiohttp_session) -> None:
        """Test server error retry logic with exponential backoff."""
        api = ActronApi("test@example.com", "password", mock_aiohttp_session)
        api.access_token = "mock_token"
        api.token_expires_at = datetime.now() + timedelta(hours=1)

        # Mock server error responses
        mock_response = MagicMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal server error")
        mock_aiohttp_session.request.return_value.__aenter__.return_value = (
            mock_response
        )

        with pytest.raises(ApiError) as exc_info:
            await api.get_ac_status("TEST123456")

        # Should have retried MAX_RETRIES times
        assert mock_aiohttp_session.request.call_count == MAX_RETRIES
        assert exc_info.value.is_server_error is True
        assert "after 3 attempts" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_client_error_no_retry(self, mock_aiohttp_session) -> None:
        """Test that client errors don't trigger retries."""
        api = ActronApi("test@example.com", "password", mock_aiohttp_session)
        api.access_token = "mock_token"
        api.token_expires_at = datetime.now() + timedelta(hours=1)

        # Mock client error response
        mock_response = MagicMock()
        mock_response.status = 400
        mock_response.text = AsyncMock(return_value="Bad request")
        mock_aiohttp_session.request.return_value.__aenter__.return_value = (
            mock_response
        )

        with pytest.raises(ApiError) as exc_info:
            await api.get_ac_status("TEST123456")

        # Should only have made one call (no retries for client errors)
        assert mock_aiohttp_session.request.call_count == 1
        assert exc_info.value.is_client_error is True
