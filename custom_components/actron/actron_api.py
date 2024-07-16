"""API for Actron Neo."""
import asyncio
import logging
import aiohttp
import json
import os
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import BASE_URL, HVAC_MODE_OFF, HVAC_MODE_HEAT, HVAC_MODE_COOL, HVAC_MODE_AUTO, HVAC_MODE_FAN

_LOGGER = logging.getLogger(__name__)

class ActronNeoAPI:
    """API client for Actron Neo."""

    def __init__(self, username: str, password: str, client_name: str, device_serial: str, storage_path: str):
        """Initialize the API client."""
        # ... (previous init code remains the same)
        self.zones = []

    # ... (previous methods remain the same)

    async def get_status(self):
        """Get the current status of the AC system."""
        headers = {
            "Authorization": f"Bearer {self.bearer_token['token']}",
            "Accept": "application/json"
        }
        request = aiohttp.RequestInfo(url=self.query_url, method="GET", headers=headers)
        
        response = await self.manage_api_request(request)
        
        # Process zones
        self.zones = []
        zone_data = response['lastKnownState']['RemoteZoneInfo']
        zone_enabled_state = response['lastKnownState']['UserAirconSettings']['EnabledZones']
        
        for index, zone in enumerate(zone_data):
            if zone['NV_Exists']:
                self.zones.append({
                    'name': zone['NV_Title'],
                    'index': index,
                    'enabled': zone_enabled_state[index],
                    'current_temp': zone['LiveTemp_oC'],
                    'set_temp_heat': zone['TemperatureSetpoint_Heat_oC'],
                    'set_temp_cool': zone['TemperatureSetpoint_Cool_oC'],
                    'min_temp': min(zone['MinHeatSetpoint'], zone['MinCoolSetpoint']),
                    'max_temp': max(zone['MaxHeatSetpoint'], zone['MaxCoolSetpoint']),
                })
        
        return response

    async def set_zone_state(self, zone_index: int, enabled: bool):
        """Enable or disable a zone."""
        command = {f"UserAirconSettings.EnabledZones[{zone_index}]": enabled}
        return await self.run_command(command)

    async def set_zone_temperature(self, zone_index: int, temp: float, mode: str):
        """Set the target temperature for a specific zone."""
        if mode == HVAC_MODE_COOL:
            command = {f"RemoteZoneInfo[{zone_index}].TemperatureSetpoint_Cool_oC": temp}
        else:
            command = {f"RemoteZoneInfo[{zone_index}].TemperatureSetpoint_Heat_oC": temp}
        return await self.run_command(command)

    # ... (other methods remain the same)