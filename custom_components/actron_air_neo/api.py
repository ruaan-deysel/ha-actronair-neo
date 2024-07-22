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

    async def login(self):
        _LOGGER.info("Attempting to log in to Actron API")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/auth/login", headers=headers, json={
                "username": self.username,
                "password": self.password
            }) as response:
                response_text = await response.text()
                _LOGGER.debug("Login response text: %s", response_text)
                data = await response.json()
                _LOGGER.debug("Login response JSON: %s", data)
                self.access_token = data["access_token"]
                self.refresh_token = data["refresh_token"]
                _LOGGER.info("Login successful, tokens obtained")

    async def refresh_token(self):
        _LOGGER.info("Attempting to refresh token")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/auth/refresh", headers=headers, json={
                "refresh_token": self.refresh_token
            }) as response:
                data = await response.json()
                _LOGGER.debug("Token refresh response: %s", data)
                self.access_token = data["access_token"]
                self.refresh_token = data["refresh_token"]
                _LOGGER.info("Token refreshed successfully")

    async def get_device_serial_number(self):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        _LOGGER.info("Fetching device serial number from Actron API")
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/hvac/device", headers=headers) as response:
                data = await response.json()
                _LOGGER.debug("Device serial number response: %s", data)
                self.device_serial_number = data.get("serialNumber")
                _LOGGER.info("Device serial number: %s", self.device_serial_number)
                return self.device_serial_number

    async def get_status(self):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        _LOGGER.info("Fetching status from Actron API")
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/hvac/status", headers=headers) as response:
                status = await response.json()
                _LOGGER.debug("Status response: %s", status)
                return status

    async def set_power_state(self, state: str):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        _LOGGER.info("Setting power state to %s", state)
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/hvac/power", headers=headers, json={"state": state}) as response:
                data = await response.json()
                _LOGGER.debug("Set power state response: %s", data)
                return data

    async def set_climate_mode(self, mode: str):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        _LOGGER.info("Setting climate mode to %s", mode)
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/hvac/mode", headers=headers, json={"mode": mode}) as response:
                data = await response.json()
                _LOGGER.debug("Set climate mode response: %s", data)
                return data

    async def set_fan_mode(self, mode: str):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        _LOGGER.info("Setting fan mode to %s", mode)
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/hvac/fan", headers=headers, json={"mode": mode}) as response:
                data = await response.json()
                _LOGGER.debug("Set fan mode response: %s", data)
                return data

    async def set_target_temperature(self, temperature: float):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        _LOGGER.info("Setting target temperature to %s", temperature)
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/hvac/temperature", headers=headers, json={"temperature": temperature}) as response:
                data = await response.json()
                _LOGGER.debug("Set target temperature response: %s", data)
                return data

    async def set_zone_state(self, zone_name: str, state: bool):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        _LOGGER.info("Setting zone %s state to %s", zone_name, state)
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/hvac/zone", headers=headers, json={"zone": zone_name, "state": state}) as response:
                data = await response.json()
                _LOGGER.debug("Set zone state response: %s", data)
                return data
