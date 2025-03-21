
# Actron Neo/Nimbus API Cheat Sheet
This document details the process of authenticating, querying and sending commands to the Actron Neo API.

The details in this document have been aquired through online research, reverse engineering and testing against the Que API using my own Actron Que account and AC system. This information is provided without garuntee or warranty of any kind and has not been validated or provided by Actron.

All requests should be sent to the Actron NEO API servers located at: `https://nimbus.actronair.com.au`

## Authentication ##
Authentication to the Actron Neo API is a two step process.  
1. Request a pairing token to authorise a new device
2. Use pairing token to request a bearer token

Following authentication the bearer token must be sent in the Authorization header for all API queries and commands.

### Request Pairing (Refresh) Token ###
Specify the details of the client in the request body. The username and password are the credentials you use to login to your Actron Neo account. Device name and ID are values that you can set to any unique value. Client must be set to one of the options shown (ios, android, windowsphone or loadtest). I have only tested with this value set to ios.

**Request**  
Method: POST  
Path: `/api/v0/client/user-devices`  
Required Headers:
 - Host: nimbus.actronair.com.au
 - Content-Length: <content_length> 
 - Content-Type: application/x-www-form-urlencoded

Content:  
username: <my_username>  
password: <my_password>  
client: ios | android | windowsphone | loadtest  
deviceName: <any_unique_name_for_authorised_device>  
deviceUniqueIdentifier: <any_unique_id_value>  

**Response**  
The response will resemble the JSON content below. You will need to extract the `pairingToken` for the next step in the authentication process.
```json
{
    "id": "<id_value>",
    "deviceName": "<name_set_in_request>",
    "pairingToken": "<token_value>",
    "expires": "<expire_time>",
    "_links": {
        "self": {
            "href": "/api/v0/client/user-devices/<id_value>"
        }
    }
}
```
### Request Bearer Token ###
Use the provided `pairingToken` (aka Refresh Token) to obtain a bearer toekn. Bearer token will be needed to authorize all subsequent API calls.  

**Request**  
Method: POST  
Path: `/api/v0/oauth/token`  
Required Headers:
 - Host: nimbus.actronair.com.au
 - Content-Length: <content_length> 
 - Content-Type: application/x-www-form-urlencoded

Content:  
grant_type: refresh_token   
refresh_token: <pairing_token>   
client_id: app

**Response**  
The response will resemble the JSON content below. You will need to extract the `pairingToken` for the next step in the authentication process.
```json
{
    "access_token": "<Some Very Long Value>",
    "token_type": "bearer",
    "expires_in": 259199
}
```
Use the value provided in `access_token` as the value of the bearer token in the Authorization header.

## Queries ##
Method: GET  
Path: variable  
Required Headers:
 - Authorization: Bearer <my_token>

Queries will be sent with an empty body and return JSON data

### List AC Systems ###
List all AC systems in the customer account. This will return the serial number of the unit you wish to control. The serial number must be set in the query string when sending commands or queries to the unit.  
Path: `/api/v0/client/ac-systems`
Parameters: `?includeNeo=true`

### Retrieve AC System Status ###
Retireves the full status of the Actron AC unit targetted. Temprature, humidty, zone details etc.  
Path: `/api/v0/client/ac-systems/status/latest?serial=<my_serail>`

### Retrieve AC System Events ###
Retireves system events.  
Path: `/api/v0/client/ac-systems/events/latest?serial=<my_serail>`

Path string can be modified to retrive specific event windows. Replace the '|' in the event ID with '%'.  
**Newer Events**  
`/api/v0/client/ac-systems/events/newer?serial=<my_serial>&newerThanEventId=<event_id>"`  
**Older Events**  
`/api/v0/client/ac-systems/events/older?serial=<my_serial>&olderThanEventId=<event_id>`

## Commands ##
Method: POST  
Path: `/api/v0/client/ac-systems/cmds/send?serial=<my_serial>`  
Required Headers:
 - Authorization: Bearer <my_token>
 - Content-Type: application/json
 

Commands are sent as JSON in the request body and have the following syntax:  
```json
{
    "command":{
        "requested.command-1": "setting",
        ...
        "requested.command-n": "setting",
        "type":"set-settings"
        }
}
```
### Operating Mode Commands ###
System ON/OFF can be triggered indebendlty or along with the desired mode setting

**Set System Mode to OFF**
```json
{
    "command":{
        "UserAirconSettings.isOn":false,
        "type":"set-settings"
        }
}
```
**Set System Mode to ON/Automatic**
```json
{
    "command":{
        "UserAirconSettings.isOn":true,
        "UserAirconSettings.Mode":"AUTO",
        "type":"set-settings"
        }
}
```
**Set System Mode to ON/Cool**
```json
{
    "command":{
        "UserAirconSettings.isOn":true,
        "UserAirconSettings.Mode":"COOL",
        "type":"set-settings"
        }
}
```
**Set System Mode to ON/Fan-Only**
```json
{
    "command":{
        "UserAirconSettings.isOn":true,
        "UserAirconSettings.Mode":"FAN",
        "type":"set-settings"
        }
}
```
**Set System Mode to ON/Heat**
```json
{
    "command":{
        "UserAirconSettings.isOn":true,
        "UserAirconSettings.Mode":"HEAT",
        "type":"set-settings"
        }
}
```
### Turn On/Off Zone ###
Zones are numbered starting at zero and will be specified within the square brackets '[]' following 'RemoteZoneInfo'.  
Random zone numbers used in following examples.

**Set Zone to OFF**
```json
{
    "command":{
        "UserAirconSettings.EnabledZones[3]":false,
        "type":"set-settings"
        }
}
```
**Set Zone to ON**
```json
{
    "command":{
        "UserAirconSettings.EnabledZones[2]":true,
        "type":"set-settings"
        }
}
```
**Set Multiple Zones ON/OFF in Single Command**
```json
{
    "command":{
        "UserAirconSettings.EnabledZones[2]":true,
        "UserAirconSettings.EnabledZones[1]":false,
        "UserAirconSettings.EnabledZones[0]":false,
        "type":"set-settings"
        }
}
```
### Fan Mode Commands ###
Fan can be set to Auto, Low, Medium or High with the option to set continuous fan by adding the '-CONT' to the end of the mode string.  

**Set Fan Mode to Auto**
```json
{
    "command":{
        "UserAirconSettings.FanMode":"AUTO" | "AUTO-CONT",
        "type":"set-settings"
        }
}
```
**Set Fan Mode to Low**
```json
{
    "command":{
        "UserAirconSettings.FanMode":"LOW" | "LOW-CONT",
        "type":"set-settings"
        }
}
```
**Set Fan Mode to Medium**
```json
{
    "command":{
        "UserAirconSettings.FanMode":"MED" | "MED-CONT",
        "type":"set-settings"
        }
}
```
**Set Fan Mode to High**
```json
{
    "command":{
        "UserAirconSettings.FanMode":"HIGH" | "HIGH-CONT",
        "type":"set-settings"
        }
}
```

### Temprature Commands ###
Temprature can be set as a floating point number within permitted ranges.  
Setting the temprature is not applicable in OFF or FAN-ONLY mode, and command will vary based on heating, cooling or auto mode. This is the setting for the common zone.  
Random set points used as an example setting in examples that follow

**Set Cooling Temp**
```json
{
    "command":{
        "UserAirconSettings.TemperatureSetpoint_Cool_oC": 20.4,
        "type":"set-settings"
        }
}
```
**Set Heating Temp**
```json
{
    "command":{
        "UserAirconSettings.TemperatureSetpoint_Heat_oC": 22.0,
        "type":"set-settings"
        }
}
```
**Set Auto Heating/Cooling Temp**
```json
{
    "command":{
        "UserAirconSettings.TemperatureSetpoint_Heat_oC": 22.0,
        "UserAirconSettings.TemperatureSetpoint_Cool_oC": 20.4,
        "type":"set-settings"
        }
}
```
### Zone Temprature Commands ###
Same as the temprature commands above but zone specific. Zones are numbered starting at zero and will be specified within the square brackets '[]' following 'RemoteZoneInfo'.  
Random set points and zone numbers used as an example setting in examples that follow

**Set Cooling Temp**
```json
{
    "command":{
        "RemoteZoneInfo[0].TemperatureSetpoint_Cool_oC": 20.4,
        "type":"set-settings"
        }
}
```
**Set Heating Temp**
```json
{
    "command":{
        "RemoteZoneInfo[3].TemperatureSetpoint_Heat_oC": 22.0,
        "type":"set-settings"
        }
}
```
**Set Auto Heating/Cooling Temp**
```json
{
    "command":{
        "RemoteZoneInfo[2].TemperatureSetpoint_Heat_oC": 22.0,
        "RemoteZoneInfo[2].TemperatureSetpoint_Cool_oC": 20.4,
        "type":"set-settings"
        }
}
```