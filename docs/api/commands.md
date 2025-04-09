# Commands

This document explains how to send commands to the ActronAir Neo API to control your air conditioning system.

## Command Structure

Commands are sent as JSON objects to the API. All commands follow this general structure:

```json
{
    "command": {
        "requested.command-1": "setting",
        "requested.command-2": "setting",
        ...
        "type": "set-settings"
    }
}
```

## Sending Commands

### Request

**Endpoint:** `POST /api/v0/client/ac-systems/cmds/send?serial={serial_number}`

**Headers:**
```
Host: nimbus.actronair.com.au
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Example Request:**
```http
POST /api/v0/client/ac-systems/cmds/send?serial=ABC123456 HTTP/1.1
Host: nimbus.actronair.com.au
Authorization: Bearer access_token_value
Content-Type: application/json

{
    "command": {
        "UserAirconSettings.isOn": true,
        "UserAirconSettings.Mode": "COOL",
        "type": "set-settings"
    }
}
```

### Response

**Success Response (200 OK):**
```json
{
    "result": "OK",
    "message": "Command sent successfully"
}
```

**Error Response (400 Bad Request):**
```json
{
    "error": {
        "code": "invalid_command",
        "message": "Invalid command format"
    }
}
```

## Common Commands

### Power Control

#### Turn System On

```json
{
    "command": {
        "UserAirconSettings.isOn": true,
        "type": "set-settings"
    }
}
```

#### Turn System Off

```json
{
    "command": {
        "UserAirconSettings.isOn": false,
        "type": "set-settings"
    }
}
```

### Mode Control

#### Set Mode to Cool

```json
{
    "command": {
        "UserAirconSettings.Mode": "COOL",
        "type": "set-settings"
    }
}
```

#### Set Mode to Heat

```json
{
    "command": {
        "UserAirconSettings.Mode": "HEAT",
        "type": "set-settings"
    }
}
```

#### Set Mode to Fan Only

```json
{
    "command": {
        "UserAirconSettings.Mode": "FAN",
        "type": "set-settings"
    }
}
```

#### Set Mode to Auto

```json
{
    "command": {
        "UserAirconSettings.Mode": "AUTO",
        "type": "set-settings"
    }
}
```

### Temperature Control

#### Set Cooling Temperature

```json
{
    "command": {
        "UserAirconSettings.TemperatureSetpoint_Cool_oC": 24.0,
        "type": "set-settings"
    }
}
```

#### Set Heating Temperature

```json
{
    "command": {
        "UserAirconSettings.TemperatureSetpoint_Heat_oC": 21.0,
        "type": "set-settings"
    }
}
```

#### Set Both Cooling and Heating Temperatures (for Auto Mode)

```json
{
    "command": {
        "UserAirconSettings.TemperatureSetpoint_Cool_oC": 24.0,
        "UserAirconSettings.TemperatureSetpoint_Heat_oC": 21.0,
        "type": "set-settings"
    }
}
```

### Fan Control

#### Set Fan Mode to Auto

```json
{
    "command": {
        "UserAirconSettings.FanMode": "AUTO",
        "type": "set-settings"
    }
}
```

#### Set Fan Mode to Low

```json
{
    "command": {
        "UserAirconSettings.FanMode": "LOW",
        "type": "set-settings"
    }
}
```

#### Set Fan Mode to Medium

```json
{
    "command": {
        "UserAirconSettings.FanMode": "MED",
        "type": "set-settings"
    }
}
```

#### Set Fan Mode to High

```json
{
    "command": {
        "UserAirconSettings.FanMode": "HIGH",
        "type": "set-settings"
    }
}
```

#### Set Fan Mode to Continuous

For continuous fan operation, append "-CONT" to the fan mode:

```json
{
    "command": {
        "UserAirconSettings.FanMode": "LOW-CONT",
        "type": "set-settings"
    }
}
```

Note: Continuous fan mode is not available with AUTO fan mode.

### Zone Control

#### Enable a Zone

```json
{
    "command": {
        "UserAirconSettings.EnabledZones[0]": true,
        "type": "set-settings"
    }
}
```

#### Disable a Zone

```json
{
    "command": {
        "UserAirconSettings.EnabledZones[0]": false,
        "type": "set-settings"
    }
}
```

#### Control Multiple Zones

```json
{
    "command": {
        "UserAirconSettings.EnabledZones[0]": true,
        "UserAirconSettings.EnabledZones[1]": true,
        "UserAirconSettings.EnabledZones[2]": false,
        "UserAirconSettings.EnabledZones[3]": false,
        "type": "set-settings"
    }
}
```

#### Set Zone Temperature (Cooling)

```json
{
    "command": {
        "RemoteZoneInfo[0].TemperatureSetpoint_Cool_oC": 23.0,
        "type": "set-settings"
    }
}
```

#### Set Zone Temperature (Heating)

```json
{
    "command": {
        "RemoteZoneInfo[0].TemperatureSetpoint_Heat_oC": 22.0,
        "type": "set-settings"
    }
}
```

### Special Modes

#### Set Away Mode

```json
{
    "command": {
        "UserAirconSettings.AwayMode": true,
        "type": "set-settings"
    }
}
```

#### Set Quiet Mode

```json
{
    "command": {
        "UserAirconSettings.QuietMode": true,
        "type": "set-settings"
    }
}
```

## Combining Commands

Multiple commands can be combined in a single request:

```json
{
    "command": {
        "UserAirconSettings.isOn": true,
        "UserAirconSettings.Mode": "COOL",
        "UserAirconSettings.FanMode": "AUTO",
        "UserAirconSettings.TemperatureSetpoint_Cool_oC": 24.0,
        "UserAirconSettings.EnabledZones[0]": true,
        "UserAirconSettings.EnabledZones[1]": true,
        "type": "set-settings"
    }
}
```

## Error Handling

The API may return various error responses:

| Error Code | Description | Resolution |
|------------|-------------|------------|
| invalid_command | The command format is invalid | Check the command structure |
| invalid_parameter | A parameter value is invalid | Check parameter values |
| device_offline | The device is offline | Check device connectivity |
| rate_limit_exceeded | Too many commands sent | Implement rate limiting |

## Implementation in the Integration

The ActronAir Neo integration provides helper methods for common commands:

```python
async def set_power(self, device_id: str, power_on: bool) -> bool:
    """Turn the AC on or off."""
    command = {
        "command": {
            "UserAirconSettings.isOn": power_on,
            "type": "set-settings"
        }
    }
    return await self.send_command(device_id, command)

async def set_mode(self, device_id: str, mode: str) -> bool:
    """Set the AC mode."""
    mode = self.validate_mode(mode)
    command = {
        "command": {
            "UserAirconSettings.Mode": mode,
            "type": "set-settings"
        }
    }
    return await self.send_command(device_id, command)
```

## Rate Limiting

The ActronAir Neo API has rate limits to prevent abuse. The integration implements rate limiting to stay within these limits:

```python
self._rate_limiter = asyncio.Semaphore(5)  # Limit to 5 concurrent requests

async def send_command(self, device_id: str, command: Dict[str, Any]) -> bool:
    """Send a command to the AC."""
    async with self._rate_limiter:
        # Send command
        # ...
```

## Next Steps

- [Queries](queries.md): Learn how to query data from the ActronAir Neo API
- [Responses](responses.md): Learn about the structure of API responses
