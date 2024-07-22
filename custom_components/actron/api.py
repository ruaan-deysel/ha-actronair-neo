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
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/auth/login", json={
                "username": self.username,
                "password": self.password
            }) as response:
                data = await response.json()
                _LOGGER.debug("Login response: %s", data)
                self.access_token = data["access_token"]
                self.refresh_token = data["refresh_token"]
                _LOGGER.info("Login successful, tokens obtained")

    async def refresh_token(self):
        _LOGGER.info("Attempting to refresh token")
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/auth/refresh", json={
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

    # Other methods for setting power state, climate mode, etc.


class ActronEntity(Entity):
    def __init__(self, api):
        self.api = api

    @property
    def should_poll(self):
        return True

    async def async_update(self):
        _LOGGER.info("Updating entity state")
        await self.api.get_status()
