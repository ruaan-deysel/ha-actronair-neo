"""Tests for the ActronAir Neo exceptions."""

import pytest

from custom_components.actronair_neo.exceptions import (
    ActronAirNeoError,
    ApiError,
    AuthenticationError,
    ConfigurationError,
    DeviceOfflineError,
    RateLimitError,
    ZoneError,
)


class TestActronAirNeoError:
    def test_base_error(self):
        err = ActronAirNeoError("base")
        assert str(err) == "base"
        assert ActronAirNeoError.translation_domain == "actronair_neo"


class TestApiError:
    def test_basic(self):
        err = ApiError("fail")
        assert err.status_code is None
        assert err.retry_after is None

    def test_with_status(self):
        err = ApiError("fail", status_code=500)
        assert err.status_code == 500

    def test_is_temporary_true(self):
        err = ApiError("fail", status_code=429)
        assert err.is_temporary is True

    def test_is_temporary_false(self):
        err = ApiError("fail", status_code=400)
        assert err.is_temporary is False

    def test_is_temporary_none(self):
        err = ApiError("fail")
        assert err.is_temporary is False

    def test_is_client_error(self):
        err = ApiError("fail", status_code=404)
        assert err.is_client_error is True
        assert err.is_server_error is False

    def test_is_server_error(self):
        err = ApiError("fail", status_code=500)
        assert err.is_server_error is True
        assert err.is_client_error is False

    def test_is_client_error_none(self):
        err = ApiError("fail")
        assert err.is_client_error is False

    def test_is_server_error_none(self):
        err = ApiError("fail")
        assert err.is_server_error is False


class TestAuthenticationError:
    def test_basic(self):
        err = AuthenticationError("auth fail")
        assert str(err) == "auth fail"
        assert AuthenticationError.translation_key == "authentication_error"

    def test_with_retry_after(self):
        err = AuthenticationError("auth fail", retry_after=60)
        assert err.retry_after == 60


class TestRateLimitError:
    def test_basic(self):
        err = RateLimitError("rate limited")
        assert err.status_code == 429
        assert RateLimitError.translation_key == "rate_limit_error"

    def test_with_retry_after(self):
        err = RateLimitError("rate limited", retry_after=30)
        assert err.retry_after == 30


class TestDeviceOfflineError:
    def test_basic(self):
        err = DeviceOfflineError("offline")
        assert err.status_code == 503
        assert err.device_id == ""
        assert DeviceOfflineError.translation_key == "device_offline_error"

    def test_with_device_id(self):
        err = DeviceOfflineError("offline", device_id="SER123")
        assert err.device_id == "SER123"

    def test_raises(self):
        with pytest.raises(DeviceOfflineError, match="offline"):
            raise DeviceOfflineError("device offline", device_id="X")


class TestConfigurationError:
    def test_basic(self):
        with pytest.raises(ConfigurationError, match="test config"):
            raise ConfigurationError("test config")

    def test_inherits(self):
        assert issubclass(ConfigurationError, Exception)

    def test_config_key(self):
        err = ConfigurationError("bad", config_key="api_key")
        assert err.config_key == "api_key"


class TestZoneError:
    def test_basic(self):
        with pytest.raises(ZoneError, match="test zone"):
            raise ZoneError("test zone")

    def test_inherits(self):
        assert issubclass(ZoneError, Exception)

    def test_zone_attributes(self):
        err = ZoneError("fail", zone_id="zone_1", zone_index=0)
        assert err.zone_id == "zone_1"
        assert err.zone_index == 0
