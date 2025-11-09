"""Tests for the ActronAir Neo config flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.actronair_neo.api import ApiError, AuthenticationError
from custom_components.actronair_neo.const import (
    CONF_ENABLE_ZONE_CONTROL,
    CONF_PASSWORD,
    CONF_REFRESH_INTERVAL,
    CONF_SERIAL_NUMBER,
    CONF_USERNAME,
    DOMAIN,
)


class TestActronConfigFlow:
    """Test the ActronAir Neo config flow."""

    @pytest.mark.asyncio
    async def test_form_user_step(self, hass: HomeAssistant) -> None:
        """Test the user step form."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {}

    @pytest.mark.asyncio
    async def test_form_user_step_invalid_auth(self, hass: HomeAssistant) -> None:
        """Test the user step with invalid authentication."""
        with patch(
            "custom_components.actronair_neo.config_flow.ActronApi"
        ) as mock_api_class:
            mock_api = MagicMock()
            mock_api.authenticate = AsyncMock(
                side_effect=AuthenticationError("Invalid credentials")
            )
            mock_api_class.return_value = mock_api

            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            result2 = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_USERNAME: "test@example.com",
                    CONF_PASSWORD: "wrong_password",
                },
            )

            assert result2["type"] == FlowResultType.FORM
            assert result2["step_id"] == "user"
            assert result2["errors"] == {"base": "invalid_auth"}

    @pytest.mark.asyncio
    async def test_form_user_step_api_error(self, hass: HomeAssistant) -> None:
        """Test the user step with API error."""
        with patch(
            "custom_components.actronair_neo.config_flow.ActronApi"
        ) as mock_api_class:
            mock_api = MagicMock()
            mock_api.authenticate = AsyncMock(side_effect=ApiError("API Error"))
            mock_api_class.return_value = mock_api

            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            result2 = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_USERNAME: "test@example.com",
                    CONF_PASSWORD: "test_password",
                },
            )

            assert result2["type"] == FlowResultType.FORM
            assert result2["step_id"] == "user"
            assert result2["errors"] == {"base": "cannot_connect"}

    @pytest.mark.asyncio
    async def test_form_user_step_unexpected_error(self, hass: HomeAssistant) -> None:
        """Test the user step with unexpected error."""
        with patch(
            "custom_components.actronair_neo.config_flow.ActronApi"
        ) as mock_api_class:
            mock_api = MagicMock()
            mock_api.authenticate = AsyncMock(side_effect=Exception("Unexpected error"))
            mock_api_class.return_value = mock_api

            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            result2 = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_USERNAME: "test@example.com",
                    CONF_PASSWORD: "test_password",
                },
            )

            assert result2["type"] == FlowResultType.FORM
            assert result2["step_id"] == "user"
            assert result2["errors"] == {"base": "unknown"}

    @pytest.mark.asyncio
    async def test_form_device_step(
        self, hass: HomeAssistant, mock_device_list
    ) -> None:
        """Test the device selection step."""
        with patch(
            "custom_components.actronair_neo.config_flow.ActronApi"
        ) as mock_api_class:
            mock_api = MagicMock()
            mock_api.authenticate = AsyncMock()
            mock_api.get_devices = AsyncMock(return_value=mock_device_list)
            mock_api_class.return_value = mock_api

            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            result2 = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_USERNAME: "test@example.com",
                    CONF_PASSWORD: "test_password",
                },
            )

            assert result2["type"] == FlowResultType.FORM
            assert result2["step_id"] == "device"
            assert "TEST123456" in str(result2["data_schema"])

    @pytest.mark.asyncio
    async def test_form_device_step_no_devices(self, hass: HomeAssistant) -> None:
        """Test the device selection step with no devices."""
        with patch(
            "custom_components.actronair_neo.config_flow.ActronApi"
        ) as mock_api_class:
            mock_api = MagicMock()
            mock_api.authenticate = AsyncMock()
            mock_api.get_devices = AsyncMock(return_value=[])
            mock_api_class.return_value = mock_api

            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            result2 = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_USERNAME: "test@example.com",
                    CONF_PASSWORD: "test_password",
                },
            )

            assert result2["type"] == FlowResultType.FORM
            assert result2["step_id"] == "device"
            assert result2["errors"] == {"base": "no_devices"}

    @pytest.mark.asyncio
    async def test_form_options_step(
        self, hass: HomeAssistant, mock_device_list
    ) -> None:
        """Test the options step."""
        with patch(
            "custom_components.actronair_neo.config_flow.ActronApi"
        ) as mock_api_class:
            mock_api = MagicMock()
            mock_api.authenticate = AsyncMock()
            mock_api.get_devices = AsyncMock(return_value=mock_device_list)
            mock_api_class.return_value = mock_api

            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            result2 = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_USERNAME: "test@example.com",
                    CONF_PASSWORD: "test_password",
                },
            )

            result3 = await hass.config_entries.flow.async_configure(
                result2["flow_id"],
                {
                    CONF_SERIAL_NUMBER: "TEST123456",
                },
            )

            assert result3["type"] == FlowResultType.FORM
            assert result3["step_id"] == "options"

    @pytest.mark.asyncio
    async def test_complete_flow_success(
        self, hass: HomeAssistant, mock_device_list
    ) -> None:
        """Test complete successful flow."""
        with patch(
            "custom_components.actronair_neo.config_flow.ActronApi"
        ) as mock_api_class:
            mock_api = MagicMock()
            mock_api.authenticate = AsyncMock()
            mock_api.get_devices = AsyncMock(return_value=mock_device_list)
            mock_api_class.return_value = mock_api

            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            result2 = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_USERNAME: "test@example.com",
                    CONF_PASSWORD: "test_password",
                },
            )

            result3 = await hass.config_entries.flow.async_configure(
                result2["flow_id"],
                {
                    CONF_SERIAL_NUMBER: "TEST123456",
                },
            )

            result4 = await hass.config_entries.flow.async_configure(
                result3["flow_id"],
                {
                    CONF_REFRESH_INTERVAL: 60,
                    CONF_ENABLE_ZONE_CONTROL: True,
                },
            )

            assert result4["type"] == FlowResultType.CREATE_ENTRY
            assert result4["title"] == "Test AC System"
            assert result4["data"] == {
                CONF_USERNAME: "test@example.com",
                CONF_PASSWORD: "test_password",
                CONF_SERIAL_NUMBER: "TEST123456",
                CONF_REFRESH_INTERVAL: 60,
                CONF_ENABLE_ZONE_CONTROL: True,
            }

    @pytest.mark.asyncio
    async def test_duplicate_entry(
        self, hass: HomeAssistant, mock_config_entry, mock_device_list
    ) -> None:
        """Test handling of duplicate entries."""
        # Add existing entry
        mock_config_entry.add_to_hass(hass)

        with patch(
            "custom_components.actronair_neo.config_flow.ActronApi"
        ) as mock_api_class:
            mock_api = MagicMock()
            mock_api.authenticate = AsyncMock()
            mock_api.get_devices = AsyncMock(return_value=mock_device_list)
            mock_api_class.return_value = mock_api

            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            result2 = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_USERNAME: "test@example.com",
                    CONF_PASSWORD: "test_password",
                },
            )

            result3 = await hass.config_entries.flow.async_configure(
                result2["flow_id"],
                {
                    CONF_SERIAL_NUMBER: "TEST123456",
                },
            )

            assert result3["type"] == FlowResultType.ABORT
            assert result3["reason"] == "already_configured"

    @pytest.mark.asyncio
    async def test_options_flow(self, hass: HomeAssistant, mock_config_entry) -> None:
        """Test options flow."""
        mock_config_entry.add_to_hass(hass)

        result = await hass.config_entries.options.async_init(
            mock_config_entry.entry_id
        )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "init"

        result2 = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                CONF_REFRESH_INTERVAL: 30,
                CONF_ENABLE_ZONE_CONTROL: False,
            },
        )

        assert result2["type"] == FlowResultType.CREATE_ENTRY
        assert result2["data"] == {
            CONF_REFRESH_INTERVAL: 30,
            CONF_ENABLE_ZONE_CONTROL: False,
        }

    @pytest.mark.asyncio
    async def test_form_validation(self, hass: HomeAssistant) -> None:
        """Test form validation."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        # Test empty username
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "",
                CONF_PASSWORD: "test_password",
            },
        )

        assert result2["type"] == FlowResultType.FORM
        assert result2["step_id"] == "user"
        # Should show form again for empty username

        # Test empty password
        result3 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "test@example.com",
                CONF_PASSWORD: "",
            },
        )

        assert result3["type"] == FlowResultType.FORM
        assert result3["step_id"] == "user"
        # Should show form again for empty password
