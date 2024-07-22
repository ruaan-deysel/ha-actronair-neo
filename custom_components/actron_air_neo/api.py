import aiohttp
import logging

_LOGGER = logging.getLogger(__name__)

class ActronApi:
    def __init__(self, username, password):
        self.base_url = "https://nimbus.actronair.com.au"
        self.username = username
        self.password = password
        self.access_token = None
        self.refresh_token = None
        self.device_serial_number = None

    async def request_pairing_token(self):
        _LOGGER.info("Requesting pairing token from Actron API")
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "username": self.username,
            "password": self.password,
            "client": "ios",
            "deviceName": "home_assistant",
            "deviceUniqueIdentifier": "home_assistant_123"
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/api/v0/client/user-devices", headers=headers, data=data) as response:
                response_text = await response.text()
                _LOGGER.debug("Pairing token response text: %s", response_text)
                try:
                    data = await response.json()
                    _LOGGER.debug("Pairing token response JSON: %s", data)
                    self.refresh_token = data["pairingToken"]
                    _LOGGER.info("Pairing token obtained successfully")
                except Exception as e:
                    _LOGGER.error("Error decoding pairing token response: %s", e)
                    raise

    async def request_bearer_token(self):
        _LOGGER.info("Requesting bearer token from Actron API")
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": "app"
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/api/v0/oauth/token", headers=headers, data=data) as response:
                response_text = await response.text()
                _LOGGER.debug("Bearer token response text: %s", response_text)
                try:
                    data = await response.json()
                    _LOGGER.debug("Bearer token response JSON: %s", data)
                    self.access_token = data["access_token"]
                    _LOGGER.info("Bearer token obtained successfully")
                except Exception as e:
                    _LOGGER.error("Error decoding bearer token response: %s", e)
                    raise

    async def login(self):
        try:
            await self.request_pairing_token()
            await self.request_bearer_token()
        except Exception as e:
            _LOGGER.error("Error during login: %s", e)
            raise

    async def get_device_serial_number(self):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        _LOGGER.info("Fetching device serial number from Actron API")
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/api/v0/client/ac-systems", headers=headers, params={"includeNeo": "true"}) as response:
                response_text = await response.text()
                _LOGGER.debug("Device serial number response text: %s", response_text)
                try:
                    data = await response.json()
                    _LOGGER.debug("Device serial number response JSON: %s", data)
                    self.device_serial_number = data[0]["serial"]
                    _LOGGER.info("Device serial number: %s", self.device_serial_number)
                    return self.device_serial_number
                except Exception as e:
                    _LOGGER.error("Error decoding device serial number response: %s", e)
                    raise

    async def get_status(self):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        _LOGGER.info("Fetching status from Actron API")
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/api/v0/client/ac-systems/status/latest", headers=headers, params={"serial": self.device_serial_number}) as response:
                response_text = await response.text()
                _LOGGER.debug("Status response text: %s", response_text)
                try:
                    status = await response.json()
                    _LOGGER.debug("Status response JSON: %s", status)
                    return status
                except Exception as e:
                    _LOGGER.error("Error decoding status response: %s", e)
                    raise

    async def set_power_state(self, state: str):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        _LOGGER.info("Setting power state to %s", state)
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/api/v0/client/ac-systems/cmds/send", headers=headers, params={"serial": self.device_serial_number}, json={"command": {"UserAirconSettings.isOn": state == "ON", "type": "set-settings"}}) as response:
                response_text = await response.text()
                _LOGGER.debug("Set power state response text: %s", response_text)
                try:
                    data = await response.json()
                    _LOGGER.debug("Set power state response JSON: %s", data)
                    return data
                except Exception as e:
                    _LOGGER.error("Error decoding set power state response: %s", e)
                    raise

    async def set_climate_mode(self, mode: str):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        _LOGGER.info("Setting climate mode to %s", mode)
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/api/v0/client/ac-systems/cmds/send", headers=headers, params={"serial": self.device_serial_number}, json={"command": {"UserAirconSettings.Mode": mode, "type": "set-settings"}}) as response:
                response_text = await response.text()
                _LOGGER.debug("Set climate mode response text: %s", response_text)
                try:
                    data = await response.json()
                    _LOGGER.debug("Set climate mode response JSON: %s", data)
                    return data
                except Exception as e:
                    _LOGGER.error("Error decoding set climate mode response: %s", e)
                    raise

    async def set_fan_mode(self, mode: str):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        _LOGGER.info("Setting fan mode to %s", mode)
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/api/v0/client/ac-systems/cmds/send", headers=headers, params={"serial": self.device_serial_number}, json={"command": {"UserAirconSettings.FanMode": mode, "type": "set-settings"}}) as response:
                response_text = await response.text()
                _LOGGER.debug("Set fan mode response text: %s", response_text)
                try:
                    data = await response.json()
                    _LOGGER.debug("Set fan mode response JSON: %s", data)
                    return data
                except Exception as e:
                    _LOGGER.error("Error decoding set fan mode response: %s", e)
                    raise

    async def set_target_temperature(self, temperature: float):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        _LOGGER.info("Setting target temperature to %s", temperature)
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/api/v0/client/ac-systems/cmds/send", headers=headers, params={"serial": self.device_serial_number}, json={"command": {"UserAirconSettings.TemperatureSetpoint_Cool_oC": temperature, "type": "set-settings"}}) as response:
                response_text = await response.text()
                _LOGGER.debug("Set target temperature response text: %s", response_text)
                try:
                    data = await response.json()
                    _LOGGER.debug("Set target temperature response JSON: %s", data)
                    return data
                except Exception as e:
                    _LOGGER.error("Error decoding set target temperature response: %s", e)
                    raise

    async def set_zone_state(self, zone_name: str, state: bool):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        _LOGGER.info("Setting zone %s state to %s", zone_name, state)
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/api/v0/client/ac-systems/cmds/send", headers=headers, params={"serial": self.device_serial_number}, json={"command": {f"UserAirconSettings.EnabledZones[{zone_name}]": state, "type": "set-settings"}}) as response:
                response_text = await response.text()
                _LOGGER.debug("Set zone state response text: %s", response_text)
                try:
                    data = await response.json()
                    _LOGGER.debug("Set zone state response JSON: %s", data)
                    return data
                except Exception as e:
                    _LOGGER.error("Error decoding set zone state response: %s", e)
                    raise
