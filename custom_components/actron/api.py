import requests
from .const import API_URL

class ActronApi:
    def __init__(self, username, password, device_name, device_id):
        self.username = username
        self.password = password
        self.device_name = device_name
        self.device_id = device_id
        self.bearer_token = None

    def authenticate(self):
        # Step 1: Request pairing token
        pairing_token = self._request_pairing_token()
        # Step 2: Request bearer token
        self.bearer_token = self._request_bearer_token(pairing_token)

    def _request_pairing_token(self):
        url = f"{API_URL}/api/v0/client/user-devices"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "username": self.username,
            "password": self.password,
            "client": "ios",
            "deviceName": self.device_name,
            "deviceUniqueIdentifier": self.device_id
        }
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        return response.json()["pairingToken"]

    def _request_bearer_token(self, pairing_token):
        url = f"{API_URL}/api/v0/oauth/token"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "refresh_token",
            "refresh_token": pairing_token,
            "client_id": "app"
        }
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        return response.json()["access_token"]

    def list_ac_systems(self):
        url = f"{API_URL}/api/v0/client/ac-systems?includeNeo=true"
        headers = {
            "Authorization": f"Bearer {self.bearer_token}"
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    def get_ac_status(self, serial):
        url = f"{API_URL}/api/v0/client/ac-systems/status/latest?serial={serial}"
        headers = {
            "Authorization": f"Bearer {self.bearer_token}"
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    def send_command(self, serial, command):
        url = f"{API_URL}/api/v0/client/ac-systems/cmds/send?serial={serial}"
        headers = {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json"
        }
        response = requests.post(url, headers=headers, json={"command": command})
        response.raise_for_status()
        return response.json()
