# ActronAir Neo/Nimbus API Cheat Sheet

This document details the process of authenticating, querying, and sending commands
to the ActronAir Neo API.

The details in this document have been acquired through online research, reverse
engineering, and testing against the Neo API. This information is provided without
guarantee or warranty of any kind and has not been validated or provided by Actron.

> **Last verified**: February 2026, against a Classic series unit (EVA150S) running
> NTW-1000 wall controller firmware v2.5.0.7.

## Base URL

All requests are sent to the ActronAir Neo (Nimbus) API:

```text
https://nimbus.actronair.com.au
```

> **Note**: ActronAir also operates a Que platform at `https://que.actronair.com.au`
> with a similar API. The `actronneoapi` Python library supports both platforms
> with auto-detection.

## Authentication

Authentication uses the **OAuth 2.0 Device Code Flow** (RFC 8628). This replaced
the earlier username/password pairing method.

### Step 1: Request a Device Code

Request a device code that the user will enter in the ActronAir app or web portal.

**Request**

```text
POST /api/v0/oauth/token
Content-Type: application/x-www-form-urlencoded
```

**Form data**:

| Parameter    | Value                                          |
| ------------ | ---------------------------------------------- |
| `client_id`  | `home_assistant`                               |
| `grant_type` | `urn:ietf:params:oauth:grant-type:device_code` |
| `scope`      | `read write`                                   |

**Response** (JSON):

```json
{
  "device_code": "<device_code>",
  "user_code": "<user_code>",
  "verification_uri": "<url>",
  "expires_in": 900,
  "interval": 5
}
```

The user must visit `verification_uri` and enter the `user_code` to authorize
the device.

### Step 2: Poll for Token

Poll the token endpoint at the specified `interval` until the user completes
authorization.

**Request**

```text
POST /api/v0/oauth/token
Content-Type: application/x-www-form-urlencoded
```

**Form data**:

| Parameter     | Value                                          |
| ------------- | ---------------------------------------------- |
| `client_id`   | `home_assistant`                               |
| `grant_type`  | `urn:ietf:params:oauth:grant-type:device_code` |
| `device_code` | `<device_code from step 1>`                    |

**Response** (success):

```json
{
  "access_token": "<bearer_token>",
  "token_type": "bearer",
  "expires_in": 259199,
  "refresh_token": "<refresh_token>"
}
```

**Response** (pending authorization):

```json
{
  "error": "authorization_pending"
}
```

### Step 3: Refresh Token

Access tokens expire (typically after ~72 hours). Use the refresh token to obtain
a new access token.

**Request**

```text
POST /api/v0/oauth/token
Content-Type: application/x-www-form-urlencoded
```

**Form data**:

| Parameter       | Value             |
| --------------- | ----------------- |
| `client_id`     | `home_assistant`  |
| `grant_type`    | `refresh_token`   |
| `refresh_token` | `<refresh_token>` |

**Response**:

```json
{
  "access_token": "<new_bearer_token>",
  "token_type": "bearer",
  "expires_in": 259199,
  "refresh_token": "<new_refresh_token>"
}
```

> **Important**: The response may include an updated `refresh_token`. Always store
> the latest refresh token from the response.

### Authorization Header

All subsequent API calls require the bearer token:

```text
Authorization: Bearer <access_token>
```

## Queries

**Method**: GET
**Headers**: `Authorization: Bearer <access_token>`

Queries are sent with an empty body and return JSON data.

### List AC Systems

List all AC systems in the customer account. Returns serial numbers needed for
all subsequent queries and commands.

```text
GET /api/v0/client/ac-systems?includeNeo=true
```

**Response**:

```json
{
  "items": [
    {
      "serial": "<serial_number>",
      "name": "<system_name>",
      "type": "<system_type>",
      "id": "<id>"
    }
  ],
  "_links": {
    "self": { "href": "/api/v0/client/ac-systems" }
  }
}
```

### Retrieve AC System Status

Retrieves the full status of the targeted AC unit including temperature, humidity,
zone details, compressor state, and all settings.

```text
GET /api/v0/client/ac-systems/status/latest?serial=<serial>
```

See [actron_api_structure.md](actron_api_structure.md) for the complete response
structure.

### ~~Retrieve AC System Events~~ (DEPRECATED)

> **WARNING**: The Events API was **disabled by Actron in July 2025**. Requests
> to these endpoints will fail with errors.

```text
GET /api/v0/client/ac-systems/events/latest?serial=<serial>
```

Previously supported pagination:

- **Newer events**:
  `/api/v0/client/ac-systems/events/newer?serial=<serial>&newerThanEventId=<id>`
- **Older events**:
  `/api/v0/client/ac-systems/events/older?serial=<serial>&olderThanEventId=<id>`

## Commands

**Method**: POST
**Headers**: `Authorization: Bearer <access_token>`, `Content-Type: application/json`

```text
POST /api/v0/client/ac-systems/cmds/send?serial=<serial>
```

Commands are sent as JSON in the request body:

```json
{
  "command": {
    "requested.command-1": "setting",
    "requested.command-n": "setting",
    "type": "set-settings"
  }
}
```

### Operating Mode Commands

System ON/OFF can be triggered independently or together with a mode setting.

**Turn OFF**

```json
{
  "command": {
    "UserAirconSettings.isOn": false,
    "type": "set-settings"
  }
}
```

**Turn ON with mode** (COOL, HEAT, FAN, AUTO)

```json
{
  "command": {
    "UserAirconSettings.isOn": true,
    "UserAirconSettings.Mode": "COOL",
    "type": "set-settings"
  }
}
```

> **Note**: Mode support varies by unit. Check `UserAirconSettings.ModeSupport`
> in the status response. Classic units may not support `AUTO` or `DRY` modes.

### Fan Mode Commands

Fan can be set to LOW, MED, HIGH, or AUTO with optional continuous fan by
appending `-CONT`.

```json
{
  "command": {
    "UserAirconSettings.FanMode": "AUTO",
    "type": "set-settings"
  }
}
```

**Valid values**: `LOW`, `LOW-CONT`, `MED`, `MED-CONT`, `HIGH`, `HIGH-CONT`,
`AUTO`, `AUTO-CONT`

> **Note**: AUTO fan is not available on all models. Check
> `AirconSystem.IndoorUnit.NV_AutoFanEnabled` and
> `AirconSystem.IndoorUnit.NV_SupportedFanModes` (bitmask: 1=LOW, 2=MED, 4=HIGH,
> 8=AUTO).

### Temperature Commands

Temperature can be set as a floating point number within permitted ranges from
`NV_Limits.UserSetpoint_oC`.

**Set cooling setpoint**

```json
{
  "command": {
    "UserAirconSettings.TemperatureSetpoint_Cool_oC": 24.0,
    "type": "set-settings"
  }
}
```

**Set heating setpoint**

```json
{
  "command": {
    "UserAirconSettings.TemperatureSetpoint_Heat_oC": 22.0,
    "type": "set-settings"
  }
}
```

**Set both (auto mode)**

```json
{
  "command": {
    "UserAirconSettings.TemperatureSetpoint_Cool_oC": 24.0,
    "UserAirconSettings.TemperatureSetpoint_Heat_oC": 22.0,
    "type": "set-settings"
  }
}
```

### Zone Commands

Zones are zero-indexed (0-7 for up to 8 zones). Check `RemoteZoneInfo[n].NV_Exists`
to determine which zones are configured.

**Enable/disable zones**

```json
{
  "command": {
    "UserAirconSettings.EnabledZones[0]": true,
    "UserAirconSettings.EnabledZones[1]": false,
    "type": "set-settings"
  }
}
```

**Set zone temperature** (for zones with individual temperature control)

```json
{
  "command": {
    "RemoteZoneInfo[0].TemperatureSetpoint_Cool_oC": 23.0,
    "RemoteZoneInfo[0].TemperatureSetpoint_Heat_oC": 21.0,
    "type": "set-settings"
  }
}
```

### Other Commands

**Quiet mode**

```json
{
  "command": {
    "UserAirconSettings.QuietMode": true,
    "type": "set-settings"
  }
}
```

**Away mode**

```json
{
  "command": {
    "UserAirconSettings.AwayMode": true,
    "type": "set-settings"
  }
}
```

**Turbo mode** (not supported on all models — check `TurboMode.Supported`)

```json
{
  "command": {
    "UserAirconSettings.TurboMode.Enabled": true,
    "type": "set-settings"
  }
}
```

## Error Responses

### Authentication Error

```json
{
  "error": "invalid_grant",
  "error_description": "The refresh token is invalid."
}
```

### Device Unavailable (503)

Returned when the AC unit is offline or unresponsive:

```json
{
  "correlationId": "<uuid>",
  "type": "unavailable",
  "value": null,
  "mwcResponseTime": "00:00:00.0000381"
}
```

### Rate Limiting

The API enforces rate limits. Avoid polling more frequently than every 30 seconds.

## Changelog

- **February 2026**: Documented OAuth2 Device Code Flow (replaced username/password).
  Documented Events API deprecation. Added mode support, fan mode bitmask, zone
  temperature, quiet mode, away mode, and turbo mode commands.
- **July 2025**: Actron disabled the Events API.
