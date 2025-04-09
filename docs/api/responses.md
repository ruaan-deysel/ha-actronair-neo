# API Responses

This document explains the structure of responses from the ActronAir Neo API and how to interpret them.

## Response Format

API responses are JSON objects with varying structures depending on the endpoint. Most responses follow these general patterns:

### Collection Responses

Responses that return collections of items typically have this structure:

```json
{
    "items": [
        {
            // Item 1 data
        },
        {
            // Item 2 data
        }
    ],
    "_links": {
        "self": {
            "href": "/api/v0/endpoint"
        },
        "related-resource": {
            "href": "/api/v0/related-endpoint",
            "title": "Description of related resource"
        }
    }
}
```

### Single Resource Responses

Responses that return a single resource typically have this structure:

```json
{
    // Resource data
    "_links": {
        "self": {
            "href": "/api/v0/endpoint/resource-id"
        }
    }
}
```

### Error Responses

Error responses typically have this structure:

```json
{
    "error": {
        "code": "error_code",
        "message": "Human-readable error message"
    }
}
```

Or for authentication errors:

```json
{
    "error": "invalid_grant",
    "error_description": "The user credentials are incorrect."
}
```

## Common Response Types

### Device List Response

Response from `GET /api/v0/client/ac-systems`:

```json
{
    "items": [
        {
            "serial": "ABC123456",
            "name": "Living Room AC",
            "type": "Neo",
            "id": "device_id_value",
            "_links": {
                "self": {
                    "href": "/api/v0/client/ac-systems/ABC123456"
                }
            }
        }
    ],
    "_links": {
        "self": {
            "href": "/api/v0/client/ac-systems"
        }
    }
}
```

### System Status Response

Response from `GET /api/v0/client/ac-systems/status/latest?serial={serial_number}`:

```json
{
    "lastKnownState": {
        "MasterInfo": {
            "LiveTemp_oC": 24.5,
            "LiveHumidity_pc": 50.0
        },
        "RemoteZoneInfo": [
            {
                "Index": 0,
                "Name": "Living Room",
                "Type": 0,
                "LiveTemp_oC": 24.5,
                "UserSetpoint_oC": 24.0,
                "UserEnabled": true,
                "TemperatureAvailable": true,
                "ControlAvailable": true,
                "Master": true,
                "LiveHumidity_pc": 50.0
            }
        ],
        "LiveAircon": {
            "Filter": {
                "NeedsAttention": false,
                "TimeToClean_days": 30
            },
            "CompressorMode": "COOL",
            "CompressorState": "RUNNING",
            "FanState": "RUNNING",
            "Defrost": false
        },
        "UserAirconSettings": {
            "isOn": true,
            "Mode": "COOL",
            "FanMode": "AUTO",
            "TemperatureSetpoint_Cool_oC": 24.0,
            "TemperatureSetpoint_Heat_oC": 21.0,
            "EnabledZones": [true, true, false, false, false, false, false, false],
            "AwayMode": false,
            "QuietMode": false
        },
        "AirconSystem": {
            "MasterSerial": "ABC123456",
            "MasterWCFirmwareVersion": "1.2.3",
            "IndoorUnit": {
                "NV_ModelNumber": "NEO-12"
            }
        },
        "Alerts": {
            "CleanFilter": false,
            "Defrosting": false
        }
    }
}
```

### Events Response

Response from `GET /api/v0/client/ac-systems/events/latest?serial={serial_number}`:

```json
{
    "items": [
        {
            "id": "event_id_value",
            "type": "status-change-broadcast",
            "pairedUserId": "user_id_value",
            "timestamp": "2023-09-01T12:00:00Z",
            "data": {
                "UserAirconSettings.isOn": true,
                "UserAirconSettings.Mode": "COOL",
                "RemoteZoneInfo[0].LiveTemp_oC": 24.5,
                "@metadata": {
                    "connectionId": "connection_id_value",
                    "server": "server_value"
                }
            }
        }
    ],
    "_links": {
        "self": {
            "href": "/api/v0/client/ac-systems/events/latest?serial=ABC123456"
        },
        "ac-newer-events": {
            "href": "/api/v0/client/ac-systems/events/newer?serial=ABC123456&newerThanEventId=event_id_value",
            "title": "Get events newer than the current set"
        },
        "ac-older-events": {
            "href": "/api/v0/client/ac-systems/events/older?serial=ABC123456&olderThanEventId=event_id_value",
            "title": "Get events older than the current set"
        }
    }
}
```

### Command Response

Response from `POST /api/v0/client/ac-systems/cmds/send?serial={serial_number}`:

```json
{
    "result": "OK",
    "message": "Command sent successfully"
}
```

## Parsing Responses

The integration parses API responses to extract relevant data. Here's how different parts of the response are handled:

### Parsing System Status

```python
def parse_system_status(response: Dict[str, Any]) -> ActronNeoData:
    """Parse the system status response."""
    last_known_state = response.get("lastKnownState", {})
    
    # Parse main info
    master_info = last_known_state.get("MasterInfo", {})
    user_settings = last_known_state.get("UserAirconSettings", {})
    live_aircon = last_known_state.get("LiveAircon", {})
    
    main_info = {
        "temperature": master_info.get("LiveTemp_oC", 0.0),
        "humidity": master_info.get("LiveHumidity_pc", 0.0),
        "is_on": user_settings.get("isOn", False),
        "mode": user_settings.get("Mode", "OFF"),
        "fan_mode": user_settings.get("FanMode", "AUTO"),
        "cool_setpoint": user_settings.get("TemperatureSetpoint_Cool_oC", 24.0),
        "heat_setpoint": user_settings.get("TemperatureSetpoint_Heat_oC", 21.0),
        "filter_status": live_aircon.get("Filter", {}).get("NeedsAttention", False),
        "filter_days_remaining": live_aircon.get("Filter", {}).get("TimeToClean_days", 0),
        "compressor_mode": live_aircon.get("CompressorMode", "OFF"),
        "compressor_state": live_aircon.get("CompressorState", "OFF"),
        "fan_state": live_aircon.get("FanState", "OFF"),
        "defrost_mode": live_aircon.get("Defrost", False),
        "away_mode": user_settings.get("AwayMode", False),
        "quiet_mode": user_settings.get("QuietMode", False)
    }
    
    # Parse zone info
    zones = []
    remote_zone_info = last_known_state.get("RemoteZoneInfo", [])
    enabled_zones = user_settings.get("EnabledZones", [])
    
    for zone in remote_zone_info:
        index = zone.get("Index", 0)
        if index < len(enabled_zones) and enabled_zones[index]:
            zones.append({
                "index": index,
                "name": zone.get("Name", f"Zone {index}"),
                "enabled": True,
                "temperature": zone.get("LiveTemp_oC", 0.0),
                "humidity": zone.get("LiveHumidity_pc", 0.0),
                "setpoint": zone.get("UserSetpoint_oC", 0.0),
                "type": str(zone.get("Type", 0)),
                "temperature_available": zone.get("TemperatureAvailable", False),
                "control_available": zone.get("ControlAvailable", False),
                "is_master": zone.get("Master", False)
            })
    
    return ActronNeoData(main_info, zones, response)
```

### Parsing Events

```python
def parse_events(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse the events response."""
    events = []
    
    for item in response.get("items", []):
        event = {
            "id": item.get("id", ""),
            "type": item.get("type", ""),
            "timestamp": item.get("timestamp", ""),
            "data": item.get("data", {})
        }
        events.append(event)
    
    return events
```

## Error Handling

The integration handles various error responses:

```python
async def _authenticated_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
    """Make an authenticated request to the API."""
    try:
        response = await self._session.request(method, url, **kwargs)
        
        if response.status == 401:
            # Authentication error
            error_data = await response.json()
            error = error_data.get("error", "")
            error_description = error_data.get("error_description", "")
            
            if error == "invalid_token":
                # Try to refresh the token
                if await self.refresh_token():
                    # Retry the request with the new token
                    return await self._authenticated_request(method, url, **kwargs)
            
            raise ActronNeoAuthenticationError(f"Authentication error: {error} - {error_description}")
        
        if response.status == 429:
            # Rate limit exceeded
            raise ActronNeoRateLimitError("Rate limit exceeded")
        
        if response.status != 200:
            # Other API error
            error_data = await response.json()
            error_code = error_data.get("error", {}).get("code", "unknown")
            error_message = error_data.get("error", {}).get("message", "Unknown error")
            
            raise ActronNeoAPIError(f"API error ({response.status}): {error_code} - {error_message}")
        
        return await response.json()
    
    except aiohttp.ClientError as e:
        # Network error
        raise ActronNeoAPIError(f"Network error: {str(e)}")
```

## Response Transformation

The integration transforms API responses into a format that's easier to use in Home Assistant:

### Main Data Structure

```python
class ActronNeoData:
    """Class to hold data from ActronAir Neo API."""
    
    def __init__(
        self,
        main: ActronNeoMainInfo,
        zones: List[ActronNeoZoneInfo],
        raw_data: ActronNeoRawData
    ) -> None:
        """Initialize the data class."""
        self.main = main
        self.zones = zones
        self.raw_data = raw_data
```

### Entity State Mapping

```python
@property
def hvac_mode(self) -> str:
    """Return the current HVAC mode."""
    if not self.coordinator.data.main["is_on"]:
        return HVACMode.OFF
    
    mode = self.coordinator.data.main["mode"]
    if mode == "COOL":
        return HVACMode.COOL
    elif mode == "HEAT":
        return HVACMode.HEAT
    elif mode == "FAN":
        return HVACMode.FAN_ONLY
    elif mode == "AUTO":
        return HVACMode.AUTO
    
    return HVACMode.OFF

@property
def fan_mode(self) -> str:
    """Return the fan mode."""
    fan_mode = self.coordinator.data.main["fan_mode"]
    
    if fan_mode == "AUTO":
        return FAN_AUTO
    elif fan_mode == "LOW" or fan_mode == "LOW-CONT":
        return FAN_LOW
    elif fan_mode == "MED" or fan_mode == "MED-CONT":
        return FAN_MEDIUM
    elif fan_mode == "HIGH" or fan_mode == "HIGH-CONT":
        return FAN_HIGH
    
    return FAN_AUTO
```

## Next Steps

- [Authentication](authentication.md): Learn about the authentication process
- [Commands](commands.md): Learn how to send commands to the API
- [Queries](queries.md): Learn how to query data from the API
