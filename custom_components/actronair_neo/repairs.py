"""Repairs for ActronAir Neo integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.repairs import ConfirmRepairFlow, RepairsFlow
from homeassistant.helpers.issue_registry import (
    IssueSeverity,
    async_create_issue,
    async_delete_issue,
)

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from .coordinator import ActronDataCoordinator


async def async_create_fix_flow(
    hass: HomeAssistant,  # noqa: ARG001
    issue_id: str,
    data: dict[str, str | int | float | None] | None,  # noqa: ARG001
) -> RepairsFlow:
    """Create flow."""
    if issue_id == "api_authentication_failed":
        return ApiAuthenticationFailedRepairFlow()
    if issue_id == "device_offline":
        return DeviceOfflineRepairFlow()
    if issue_id == "sensor_unavailable":
        return SensorUnavailableRepairFlow()
    return ConfirmRepairFlow()


class ApiAuthenticationFailedRepairFlow(RepairsFlow):
    """Handler for API authentication failures."""

    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> dict[str, Any]:
        """Handle the initial step."""
        if user_input is not None:
            # Mark as resolved - user will need to reconfigure integration
            return self.async_create_entry(data={})

        return self.async_show_form(
            step_id="init",
            description_placeholders={
                "title": "ActronAir Neo Authentication Failed",
                "description": (
                    "The integration cannot authenticate with ActronAir servers. "
                    "This usually happens when:\n\n"
                    "• Your ActronAir account password has changed\n"
                    "• Your account has been suspended or deactivated\n"
                    "• ActronAir servers are experiencing issues\n\n"
                    "To resolve this issue:\n"
                    "1. Verify your ActronAir account credentials\n"
                    "2. Try logging into the ActronAir Neo app\n"
                    "3. If successful, restart Home Assistant\n"
                    "4. If the issue persists, reconfigure the integration"
                ),
            },
        )


class DeviceOfflineRepairFlow(RepairsFlow):
    """Handler for device offline issues."""

    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> dict[str, Any]:
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(data={})

        return self.async_show_form(
            step_id="init",
            description_placeholders={
                "title": "ActronAir Neo Device Offline",
                "description": (
                    "Your ActronAir Neo system appears to be offline. "
                    "This can happen when:\n\n"
                    "• The system has lost WiFi connectivity\n"
                    "• The system is powered off\n"
                    "• Network connectivity issues\n"
                    "• ActronAir cloud service issues\n\n"
                    "To resolve this issue:\n"
                    "1. Check that your AC system is powered on\n"
                    "2. Verify WiFi connectivity on the system display\n"
                    "3. Check your internet connection\n"
                    "4. Try using the ActronAir Neo mobile app\n"
                    "5. If the app works, restart Home Assistant"
                ),
            },
        )


class SensorUnavailableRepairFlow(RepairsFlow):
    """Handler for sensor unavailability issues."""

    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> dict[str, Any]:
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(data={})

        return self.async_show_form(
            step_id="init",
            description_placeholders={
                "title": "ActronAir Neo Sensors Unavailable",
                "description": (
                    "Some sensors are reporting unavailable status. "
                    "This typically occurs when:\n\n"
                    "• Zone sensors have low battery levels\n"
                    "• Wireless sensors have poor signal strength\n"
                    "• Sensors are disconnected or malfunctioning\n"
                    "• System configuration has changed\n\n"
                    "To resolve this issue:\n"
                    "1. Check battery levels in zone sensors\n"
                    "2. Verify sensor signal strength\n"
                    "3. Check sensor placement and obstructions\n"
                    "4. Restart the integration if sensors are working\n"
                    "5. Contact ActronAir support for hardware issues"
                ),
            },
        )


async def async_check_issues(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Check for common issues and create repair notifications."""
    coordinator: ActronDataCoordinator = entry.runtime_data

    # Check API authentication status
    if coordinator.api.error_count > 5:  # noqa: PLR2004
        async_create_issue(
            hass,
            DOMAIN,
            "api_authentication_failed",
            is_fixable=True,
            severity=IssueSeverity.ERROR,
            translation_key="api_authentication_failed",
            translation_placeholders={
                "device_name": coordinator.device_id,
                "error_count": str(coordinator.api.error_count),
            },
        )
    else:
        async_delete_issue(hass, DOMAIN, "api_authentication_failed")

    # Check device connectivity
    if not coordinator.last_update_success:
        async_create_issue(
            hass,
            DOMAIN,
            "device_offline",
            is_fixable=True,
            severity=IssueSeverity.WARNING,
            translation_key="device_offline",
            translation_placeholders={
                "device_name": coordinator.device_id,
            },
        )
    else:
        async_delete_issue(hass, DOMAIN, "device_offline")

    # Check sensor availability
    unavailable_sensors = []
    for zone_id, zone_data in coordinator.data.get("zones", {}).items():
        if zone_data.get("temp") is None and zone_data.get("capabilities", {}).get(
            "exists", False
        ):
            unavailable_sensors.append(zone_data.get("name", zone_id))

    if unavailable_sensors:
        async_create_issue(
            hass,
            DOMAIN,
            "sensor_unavailable",
            is_fixable=True,
            severity=IssueSeverity.WARNING,
            translation_key="sensor_unavailable",
            translation_placeholders={
                "device_name": coordinator.device_id,
                "sensor_count": str(len(unavailable_sensors)),
                "sensor_names": ", ".join(unavailable_sensors[:3]),
            },
        )
    else:
        async_delete_issue(hass, DOMAIN, "sensor_unavailable")


async def async_health_check(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:  # noqa: ARG001
    """Perform comprehensive health check."""
    coordinator: ActronDataCoordinator = entry.runtime_data

    health_status: dict[str, Any] = {
        "overall_status": "healthy",
        "issues": [],
        "recommendations": [],
        "system_info": {
            "api_error_count": coordinator.api.error_count,
            "last_successful_update": coordinator.api.last_successful_request,
            "cache_size": len(
                coordinator.api.response_cache._cache  # noqa: SLF001
            ),
        },
    }

    # Check API health
    if coordinator.api.error_count > 3:  # noqa: PLR2004
        err_count = coordinator.api.error_count
        severity = (
            "warning" if err_count < 10 else "error"  # noqa: PLR2004
        )
        health_status["issues"].append(
            {
                "type": "api_errors",
                "severity": severity,
                "message": (f"High API error count: {err_count}"),
                "recommendation": (
                    "Check network connectivity and ActronAir service status"
                ),
            }
        )
        health_status["overall_status"] = "degraded"

    # Check zone sensor health
    for zone_id, zone_data in coordinator.data.get("zones", {}).items():
        if (
            zone_data.get("battery_level") is not None
            and zone_data["battery_level"] < 20  # noqa: PLR2004
        ):
            zone_name = zone_data.get("name", zone_id)
            battery = zone_data["battery_level"]
            health_status["issues"].append(
                {
                    "type": "low_battery",
                    "severity": "warning",
                    "message": (f"Zone {zone_name} has low battery: {battery}%"),
                    "recommendation": "Replace zone sensor battery",
                }
            )

        if (
            zone_data.get("signal_strength") is not None
            and zone_data["signal_strength"] < -70  # noqa: PLR2004
        ):
            zone_name = zone_data.get("name", zone_id)
            signal = zone_data["signal_strength"]
            health_status["issues"].append(
                {
                    "type": "poor_signal",
                    "severity": "warning",
                    "message": (f"Zone {zone_name} has poor signal: {signal} dBm"),
                    "recommendation": (
                        "Check sensor placement and remove obstructions"
                    ),
                }
            )

    # Set overall status based on issues
    if any(issue["severity"] == "error" for issue in health_status["issues"]):
        health_status["overall_status"] = "unhealthy"
    elif health_status["issues"]:
        health_status["overall_status"] = "degraded"

    return health_status
