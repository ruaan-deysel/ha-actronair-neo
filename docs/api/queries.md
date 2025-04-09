# Queries

This document explains how to query data from the ActronAir Neo API to retrieve information about your air conditioning system.

## Query Structure

Queries are sent as GET requests to the API. The response is a JSON object containing the requested data.

## Common Queries

### List AC Systems

Retrieves a list of all AC systems associated with your account.

#### Request

**Endpoint:** `GET /api/v0/client/ac-systems?includeNeo=true`

**Headers:**
```
Host: nimbus.actronair.com.au
Authorization: Bearer {access_token}
```

**Example Request:**
```http
GET /api/v0/client/ac-systems?includeNeo=true HTTP/1.1
Host: nimbus.actronair.com.au
Authorization: Bearer access_token_value
```

#### Response

**Success Response (200 OK):**
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

### Get System Status

Retrieves the current status of a specific AC system.

#### Request

**Endpoint:** `GET /api/v0/client/ac-systems/status/latest?serial={serial_number}`

**Headers:**
```
Host: nimbus.actronair.com.au
Authorization: Bearer {access_token}
```

**Example Request:**
```http
GET /api/v0/client/ac-systems/status/latest?serial=ABC123456 HTTP/1.1
Host: nimbus.actronair.com.au
Authorization: Bearer access_token_value
```

#### Response

**Success Response (200 OK):**
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
            },
            {
                "Index": 1,
                "Name": "Bedroom",
                "Type": 0,
                "LiveTemp_oC": 23.5,
                "UserSetpoint_oC": 23.0,
                "UserEnabled": true,
                "TemperatureAvailable": true,
                "ControlAvailable": true,
                "Master": false,
                "LiveHumidity_pc": 48.0
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

### Get System Events

Retrieves recent events for a specific AC system.

#### Request

**Endpoint:** `GET /api/v0/client/ac-systems/events/latest?serial={serial_number}`

**Headers:**
```
Host: nimbus.actronair.com.au
Authorization: Bearer {access_token}
```

**Example Request:**
```http
GET /api/v0/client/ac-systems/events/latest?serial=ABC123456 HTTP/1.1
Host: nimbus.actronair.com.au
Authorization: Bearer access_token_value
```

#### Response

**Success Response (200 OK):**
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

### Get Newer Events

Retrieves events newer than a specific event ID.

#### Request

**Endpoint:** `GET /api/v0/client/ac-systems/events/newer?serial={serial_number}&newerThanEventId={event_id}`

**Headers:**
```
Host: nimbus.actronair.com.au
Authorization: Bearer {access_token}
```

**Example Request:**
```http
GET /api/v0/client/ac-systems/events/newer?serial=ABC123456&newerThanEventId=event_id_value HTTP/1.1
Host: nimbus.actronair.com.au
Authorization: Bearer access_token_value
```

### Get Older Events

Retrieves events older than a specific event ID.

#### Request

**Endpoint:** `GET /api/v0/client/ac-systems/events/older?serial={serial_number}&olderThanEventId={event_id}`

**Headers:**
```
Host: nimbus.actronair.com.au
Authorization: Bearer {access_token}
```

**Example Request:**
```http
GET /api/v0/client/ac-systems/events/older?serial=ABC123456&olderThanEventId=event_id_value HTTP/1.1
Host: nimbus.actronair.com.au
Authorization: Bearer access_token_value
```

## Data Structure

### MasterInfo

Contains information about the main unit.

| Field | Type | Description |
|-------|------|-------------|
| LiveTemp_oC | float | Current temperature in degrees Celsius |
| LiveHumidity_pc | float | Current humidity in percent |

### RemoteZoneInfo

Contains information about each zone.

| Field | Type | Description |
|-------|------|-------------|
| Index | int | Zone index (0-7) |
| Name | string | Zone name |
| Type | int | Zone type |
| LiveTemp_oC | float | Current temperature in degrees Celsius |
| UserSetpoint_oC | float | Target temperature in degrees Celsius |
| UserEnabled | boolean | Whether the zone is enabled |
| TemperatureAvailable | boolean | Whether temperature sensing is available |
| ControlAvailable | boolean | Whether the zone can be controlled |
| Master | boolean | Whether this is the master zone |
| LiveHumidity_pc | float | Current humidity in percent |

### LiveAircon

Contains information about the current state of the air conditioner.

| Field | Type | Description |
|-------|------|-------------|
| Filter.NeedsAttention | boolean | Whether the filter needs cleaning |
| Filter.TimeToClean_days | int | Days until filter cleaning is recommended |
| CompressorMode | string | Current compressor mode (COOL, HEAT, etc.) |
| CompressorState | string | Current compressor state (RUNNING, OFF, etc.) |
| FanState | string | Current fan state (RUNNING, OFF, etc.) |
| Defrost | boolean | Whether defrost mode is active |

### UserAirconSettings

Contains user-configurable settings.

| Field | Type | Description |
|-------|------|-------------|
| isOn | boolean | Whether the system is on |
| Mode | string | Current mode (COOL, HEAT, FAN, AUTO) |
| FanMode | string | Current fan mode (AUTO, LOW, MED, HIGH) |
| TemperatureSetpoint_Cool_oC | float | Cooling setpoint in degrees Celsius |
| TemperatureSetpoint_Heat_oC | float | Heating setpoint in degrees Celsius |
| EnabledZones | boolean[] | Array of zone enabled states |
| AwayMode | boolean | Whether away mode is active |
| QuietMode | boolean | Whether quiet mode is active |

### AirconSystem

Contains system information.

| Field | Type | Description |
|-------|------|-------------|
| MasterSerial | string | Serial number of the master unit |
| MasterWCFirmwareVersion | string | Firmware version |
| IndoorUnit.NV_ModelNumber | string | Model number |

### Alerts

Contains system alerts.

| Field | Type | Description |
|-------|------|-------------|
| CleanFilter | boolean | Whether the filter needs cleaning |
| Defrosting | boolean | Whether defrost mode is active |

## Error Handling

The API may return various error responses:

| Error Code | Description | Resolution |
|------------|-------------|------------|
| unauthorized | Authentication required | Re-authenticate |
| device_not_found | Device not found | Check serial number |
| rate_limit_exceeded | Too many requests | Implement rate limiting |

## Implementation in the Integration

The ActronAir Neo integration provides helper methods for common queries:

```python
async def get_devices(self) -> List[ActronNeoDeviceInfo]:
    """Get a list of available devices."""
    url = f"{self.BASE_URL}/api/v0/client/ac-systems?includeNeo=true"
    response = await self._authenticated_request("GET", url)
    
    devices = []
    for item in response.get("items", []):
        devices.append({
            "serial": item.get("serial", ""),
            "name": item.get("name", ""),
            "type": item.get("type", ""),
            "id": item.get("id", "")
        })
    
    return devices

async def get_system_status(self, device_id: str) -> Dict[str, Any]:
    """Get the current status of a device."""
    url = f"{self.BASE_URL}/api/v0/client/ac-systems/status/latest?serial={device_id}"
    return await self._authenticated_request("GET", url)
```

## Rate Limiting

The ActronAir Neo API has rate limits to prevent abuse. The integration implements rate limiting to stay within these limits:

```python
self._rate_limiter = asyncio.Semaphore(5)  # Limit to 5 concurrent requests

async def _authenticated_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
    """Make an authenticated request to the API."""
    async with self._rate_limiter:
        # Make request
        # ...
```

## Next Steps

- [Commands](commands.md): Learn how to send commands to the ActronAir Neo API
- [Responses](responses.md): Learn about the structure of API responses
