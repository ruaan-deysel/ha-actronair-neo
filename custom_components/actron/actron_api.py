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
        self.username = username
        self.password = password
        self.client_name = client_name
        self.device_serial = device_serial
        self.storage_path = storage_path
        self.command_url = None
        self.query_url = None
        self.api_client_id = self.generate_client_id()
        self.refresh_token = {"expires": 0, "token": ""}
        self.bearer_token = {"expires": 0, "token": ""}
        self.session = None
        self.zones = []

    def generate_client_id(self):
        """Generate a unique client ID."""
        import random
        random_number = random.randint(10001, 99999)
        return f"{self.client_name}-{random_number}"

    async def actron_que_api(self):
        """Initialize the API connection."""
        await self.token_generator()
        await self.get_ac_systems()
        self.command_url = f"{BASE_URL}/api/v0/client/ac-systems/cmds/send?serial={self.device_serial}"
        self.query_url = f"{BASE_URL}/api/v0/client/ac-systems/status/latest?serial={self.device_serial}"

    async def manage_api_request(self, request_content, retries=3, delay=3):
        """Manage API requests with retry logic."""
        async with aiohttp.ClientSession() as session:
            for _ in range(retries):
                try:
                    async with session.request(
                        method=request_content.method,
                        url=request_content.url,
                        headers=request_content.headers,
                        data=request_content.data
                    ) as response:
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 401:
                            await self.token_generator()
                            request_content.headers["Authorization"] = f"Bearer {self.bearer_token['token']}"
                        elif 500 <= response.status < 600:
                            await asyncio.sleep(delay)
                        else:
                            raise Exception(f"API request failed with status {response.status}")
                except Exception as e:
                    _LOGGER.error(f"API request failed: {str(e)}")
                    await asyncio.sleep(delay)
            
            raise Exception("Max retries exceeded")

    async def get_refresh_token(self):
        """Get a refresh token from the API."""
        url = f"{BASE_URL}/api/v0/client/user-devices"
        data = {
            "username": self.username,
            "password": self.password,
            "deviceName": self.client_name,
            "deviceUniqueIdentifier": self.api_client_id,
            "client": "ios",
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        request = aiohttp.RequestInfo(url=url, method="POST", headers=headers, data=data)
        
        response = await self.manage_api_request(request)
        
        self.refresh_token = {
            "expires": datetime.fromisoformat(response["expires"]).timestamp(),
            "token": response["pairingToken"]
        }
        
        # Save to file
        with open(os.path.join(self.storage_path, "refresh_token.json"), "w") as f:
            json.dump(self.refresh_token, f)

    async def get_bearer_token(self):
        """Get a bearer token using the refresh token."""
        url = f"{BASE_URL}/api/v0/oauth/token"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token["token"],
            "client_id": "app",
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        request = aiohttp.RequestInfo(url=url, method="POST", headers=headers, data=data)
        
        response = await self.manage_api_request(request)
        
        expires_at = datetime.now() + timedelta(seconds=response["expires_in"] - 300)
        self.bearer_token = {
            "expires": expires_at.timestamp(),
            "token": response["access_token"]
        }
        
        # Save to file
        with open(os.path.join(self.storage_path, "bearer_token.json"), "w") as f:
            json.dump(self.bearer_token, f)

    async def token_generator(self):
        """Generate or refresh tokens as needed."""
        now = datetime.now().timestamp()
        
        if self.refresh_token["expires"] <= now:
            await self.get_refresh_token()
            await self.get_bearer_token()
        elif self.bearer_token["expires"] <= now:
            await self.get_bearer_token()

    async def get_ac_systems(self):
        """Get AC system information."""
        url = f"{BASE_URL}/api/v0/client/ac-systems?includeNeo=true"
        headers = {"Authorization": f"Bearer {self.bearer_token['token']}"}
        request = aiohttp.RequestInfo(url=url, method="GET", headers=headers)
        
        response = await self.manage_api_request(request)
        
        systems = response["_embedded"]["ac-system"]
        if len(systems) == 1 or not self.device_serial:
            self.device_serial = systems[0]["serial"]
        elif self.device_serial:
            for system in systems:
                if system["serial"] == self.device_serial:
                    break
            else:
                raise Exception(f"Device with serial {self.device_serial} not found")
        else:
            raise Exception("Multiple AC systems found, please specify a device_serial")

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

    async def set_hvac_mode(self, mode):
        """Set the HVAC mode."""
        mode_mapping = {
            HVAC_MODE_OFF: False,
            HVAC_MODE_COOL: "COOL",
            HVAC_MODE_HEAT: "HEAT",
            HVAC_MODE_AUTO: "AUTO",
            HVAC_MODE_FAN: "FAN"
        }
        if mode == HVAC_MODE_OFF:
            command = {"UserAirconSettings.isOn": False}
        else:
            command = {"UserAirconSettings.isOn": True, "UserAirconSettings.Mode": mode_mapping[mode]}
        return await self.run_command(command)

    async def set_fan_mode(self, mode):
        """Set the fan mode."""
        command = {"UserAirconSettings.FanMode": mode}
        return await self.run_command(command)

    async def run_command(self, command):
        """Send a command to the AC system."""
        headers = {
            "Authorization": f"Bearer {self.bearer_token['token']}",
            "Content-Type": "application/json"
        }
        data = json.dumps({"command": {**command, "type": "set-settings"}})
        request = aiohttp.RequestInfo(url=self.command_url, method="POST", headers=headers, data=data)
        
        response = await self.manage_api_request(request)
        
        if response.get("type") == "ack":
            return True
        return False