# ActronAir Neo API Structure Documentation

This document outlines the structure of the ActronAir Neo API responses based on exploration with the ActronAir Neo API Explorer tool.

## Table of Contents

- [Authentication](#authentication)
- [Device Information](#device-information)
- [Status API Response](#status-api-response)
- [Events API Response](#events-api-response)
- [Command Structure](#command-structure)
- [Error Responses](#error-responses)

## Authentication

### OAuth Token Endpoint

**URL**: `/api/v0/oauth/token`

**Method**: POST

**Request Body**:

```json
{
  "grant_type": "refresh_token",
  "refresh_token": "your_refresh_token",
  "client_id": "Neo App"
}
```

**Response Structure**:

```json
{
  "access_token": "string",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "string"
}
```

### User Devices Endpoint (for initial pairing)

**URL**: `/api/v0/client/user-devices`

**Method**: POST

**Headers**:

```
Content-Type: application/x-www-form-urlencoded
```

**Form Data**:

```
username: your_username
password: your_password
client: ios
deviceName: ActronExplorer
```

**Response Structure**:

```json
{
  "refresh_token": "string",
  "user_id": "string"
}
```

## Device Information

### Listing AC Systems

**URL**: `/api/v0/client/ac-systems`

**Method**: GET

**Headers**:

```
Authorization: Bearer your_access_token
```

**Response Structure**:

```json
{
  "items": [
    {
      "serial": "string",
      "name": "string",
      "type": "string",
      "id": "string"
    }
  ],
  "_links": {
    "self": {
      "href": "string"
    }
  }
}
```

## Status API Response

### AC System Status

**URL**: `/api/v0/client/ac-systems/status/latest?serial=your_serial_number`

**Method**: GET

**Headers**:

```
Authorization: Bearer your_access_token
```

**Response Structure**:

```json
{
  "RemoteZoneInfo": [
    {
      "Index": 0,
      "Name": "string",
      "Type": 0,
      "LiveTemp_oC": 24.0,
      "UserSetpoint_oC": 24.0,
      "UserEnabled": true,
      "TemperatureAvailable": true,
      "ControlAvailable": true,
      "Master": true,
      "LiveHumidity_pc": 50
    },
    // Additional zones...
  ],
  "LiveAircon": {
    "Filter": {
      "NeedsAttention": false,
      "TimeToClean_days": 0
    },
    "CompressorMode": "string", // "COOL", "HEAT", "FAN", etc.
    "CompressorState": "string",
    "FanState": "string",
    "MasterSensor": {
      "UseForControlSetpoint": false,
      "UseForFreezeProtection": false,
      "UseForTemperature": false,
      "UseForHumidity": false,
      "UseForClock": false,
      "FromMaster": false,
      "FromCommissioning": false
    },
    "ESPMode": false,
    "Warnings": [],
    "Defrost": false,
    "OutdoorUnit": {
      "RoomTemp": 0.0,
      "LastModified": "string",
      "ReverseValvePosition": "string",
      "DefrostMode": 0
    }
  },
  "Firmware": {
    "FirmwareComponents": [
      {
        "Component": "string",
        "Version": "string"
      }
    ],
    "FirmwareHistory": [],
    "LastModified": "string"
  },
  "Logs": {
    "NV_WC_EventHistory": [
      {
        "Id": 0,
        "Task": "string",
        "TimeStamp": "string",
        "Event": "string",
        "Parameters": []
      }
    ]
  },
  "Installer": {
    "Id": "string",
    "Name": "string",
    "Email": "string",
    "Phone": "string"
  },
  "UserAirconSettings": {
    "AfterHours": {
      "Enabled": false,
      "Duration": 120
    },
    "ApplicationMode": "string", // "Residential"
    "AwayMode": false,
    "EnabledZones": [
      true,
      false,
      false,
      true,
      false,
      false,
      false,
      false
    ],
    "FanMode": "string", // "HIGH", "MEDIUM", "LOW"
    "Mode": "string", // "COOL", "HEAT", "FAN", "AUTO"
    "NV_SavedZoneState": [
      true,
      false,
      false,
      true,
      false,
      false,
      false,
      false
    ],
    "QuietMode": true,
    "QuietModeEnabled": true,
    "QuietModeActive": false,
    "ServiceReminder": {
      "Enabled": false,
      "Time": "string"
    },
    "VFT": {
      "Airflow": 0.0,
      "StaticPressure": 0.0,
      "Supported": false,
      "Enabled": false,
      "SelfLearn": {
        "LastRunTime": "string",
        "CurrentState": "string",
        "LastResult": "string",
        "MaxStaticPressure": 0
      }
    },
    "TurboMode": {
      "Supported": false,
      "Enabled": false
    },
    "TemperatureSetpoint_Cool_oC": 24.0,
    "TemperatureSetpoint_Heat_oC": 24.0,
    "ZoneTemperatureSetpointVariance_oC": 2.0,
    "isFastHeating": false,
    "isOn": true,
    "ChangeSrc": {
      "Mode": "string",
      "isOn": "string"
    }
  }
}
```

## Events API Response

### AC System Events

**URL**: `/api/v0/client/ac-systems/events/latest?serial=your_serial_number`

**Method**: GET

**Headers**:

```
Authorization: Bearer your_access_token
```

**Response Structure**:

```json
{
  "items": [
    {
      "id": "string",
      "type": "status-change-broadcast",
      "pairedUserId": "string",
      "timestamp": "string",
      "data": {
        // Various property changes, examples:
        "LiveAircon.Defrost": false,
        "LiveAircon.OutdoorUnit.DefrostMode": 0,
        "LiveAircon.CompressorMode": "COOL",
        "RemoteZoneInfo[0].LiveTemp_oC": 24.0,
        "@metadata": {
          "connectionId": "string",
          "server": "string"
        }
      }
    }
  ],
  "_links": {
    "self": {
      "href": "string"
    },
    "ac-newer-events": {
      "href": "string",
      "title": "Get events newer than the current set"
    },
    "ac-older-events": {
      "href": "string",
      "title": "Get events older than the current set"
    }
  }
}
```

## Command Structure

### Send Command

**URL**: `/api/v0/client/ac-systems/cmds/send?serial=your_serial_number`

**Method**: POST

**Headers**:

```
Authorization: Bearer your_access_token
Content-Type: application/json
```

**Common Command Examples**:

#### Turn AC On

```json
{
  "UserAirconSettings.isOn": true
}
```

#### Turn AC Off

```json
{
  "UserAirconSettings.isOn": false
}
```

#### Set Mode (Cool, Heat, Fan, Auto)

```json
{
  "UserAirconSettings.Mode": "COOL"
}
```

#### Set Fan Mode

```json
{
  "UserAirconSettings.FanMode": "HIGH"
}
```

#### Set Temperature

```json
{
  "UserAirconSettings.TemperatureSetpoint_Cool_oC": 24.0
}
```

#### Control Zone

```json
{
  "UserAirconSettings.EnabledZones[0]": true
}
```

**Response Structure**:

```json
{
  "result": "OK",
  "message": "Command sent successfully"
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

### API Error

```json
{
  "error": {
    "code": "string",
    "message": "string"
  }
}
```

### Rate Limit Error

```json
{
  "error": {
    "code": "rate_limit_exceeded",
    "message": "Rate limit has been exceeded"
  }
}
```
