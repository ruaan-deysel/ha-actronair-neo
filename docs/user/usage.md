# Usage Guide

This guide explains how to use the ActronAir Neo integration in Home Assistant after installation and configuration.

## Climate Control

The main climate entity allows you to control your ActronAir Neo system's primary functions.

### Climate Entity Card

The climate entity appears in your Home Assistant dashboard as a climate card:

![Climate Card](../assets/images/climate_card.png)

### Available Controls

From the climate card, you can:

- **Power**: Turn the system on or off
- **Mode**: Switch between Heat, Cool, Fan Only, and Auto modes
- **Temperature**: Set the target temperature
- **Fan Speed**: Select Low, Medium, High, or Auto fan speeds

### Climate Modes

| Mode | Description |
|------|-------------|
| Heat | System will heat the space to the target temperature |
| Cool | System will cool the space to the target temperature |
| Fan Only | Only the fan will run, no heating or cooling |
| Auto | System will automatically switch between heating and cooling to maintain the target temperature |

### Fan Modes

| Fan Mode | Description |
|----------|-------------|
| Low | Fan runs at low speed |
| Medium | Fan runs at medium speed |
| High | Fan runs at high speed |
| Auto | Fan speed is automatically adjusted based on the difference between current and target temperatures |

## Zone Control

If you have enabled zone control during configuration, you'll have additional entities for controlling individual zones.

### Zone Climate Entities

Each zone has its own climate entity that allows you to:

- Turn the zone on or off
- Set a zone-specific target temperature
- View the current temperature in that zone

### Zone Switches

You can also control zones using switch entities:

![Zone Switches](../assets/images/zone_switches.png)

These switches allow you to quickly enable or disable specific zones without changing other settings.

## Sensors

The integration creates several sensor entities that provide information about your system:

### Temperature Sensors

- **Main Temperature**: The temperature reading from the main unit
- **Zone Temperatures**: Individual temperature readings for each zone

### Humidity Sensors

- **Main Humidity**: The humidity reading from the main unit
- **Zone Humidity**: Individual humidity readings for zones that support it

### System Status Sensors

- **Filter Status**: Indicates if the filter needs cleaning
- **System Health**: Shows the overall health status of the system
- **Operating Mode**: Displays the current operating mode (heating, cooling, etc.)

## Automations

You can create powerful automations using the ActronAir Neo integration. Here are some examples:

### Schedule-Based Control

```yaml
# Turn on AC in cooling mode before arriving home
automation:
  - alias: "Pre-cool Home Before Arrival"
    trigger:
      - platform: time
        at: "16:30:00"
    condition:
      - condition: state
        entity_id: binary_sensor.someone_home
        state: "off"
      - condition: numeric_state
        entity_id: sensor.outside_temperature
        above: 25
    action:
      - service: climate.set_hvac_mode
        target:
          entity_id: climate.actronair_neo
        data:
          hvac_mode: cool
      - service: climate.set_temperature
        target:
          entity_id: climate.actronair_neo
        data:
          temperature: 24
```

### Temperature-Based Control

```yaml
# Turn on heating when temperature drops below threshold
automation:
  - alias: "Auto Heating When Cold"
    trigger:
      - platform: numeric_state
        entity_id: sensor.actronair_neo_temperature
        below: 18
        for:
          minutes: 10
    condition:
      - condition: state
        entity_id: binary_sensor.someone_home
        state: "on"
    action:
      - service: climate.set_hvac_mode
        target:
          entity_id: climate.actronair_neo
        data:
          hvac_mode: heat
      - service: climate.set_temperature
        target:
          entity_id: climate.actronair_neo
        data:
          temperature: 21
```

### Zone-Based Control

```yaml
# Turn on specific zones based on room occupancy
automation:
  - alias: "Control Zones Based on Occupancy"
    trigger:
      - platform: state
        entity_id: binary_sensor.living_room_occupancy
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.actronair_neo_zone_living_room
        data: {}
      - service: switch.turn_off
        target:
          entity_id: switch.actronair_neo_zone_bedroom
        data: {}
      - service: climate.set_temperature
        target:
          entity_id: climate.actronair_neo_zone_living_room
        data:
          temperature: 23
```

## Lovelace UI Examples

Here are some examples of how to integrate ActronAir Neo entities into your Lovelace UI:

### Basic Climate Card

```yaml
type: thermostat
entity: climate.actronair_neo
```

### Detailed Climate Card

```yaml
type: entities
title: ActronAir Neo System
entities:
  - entity: climate.actronair_neo
  - entity: sensor.actronair_neo_temperature
  - entity: sensor.actronair_neo_humidity
  - entity: binary_sensor.actronair_neo_filter_status
  - entity: sensor.actronair_neo_operating_mode
```

### Zone Control Panel

```yaml
type: entities
title: Zone Control
entities:
  - entity: switch.actronair_neo_zone_living_room
  - entity: switch.actronair_neo_zone_kitchen
  - entity: switch.actronair_neo_zone_master_bedroom
  - entity: switch.actronair_neo_zone_bedroom_2
```

## Next Steps

For troubleshooting common issues, see the [Troubleshooting Guide](troubleshooting.md).

For frequently asked questions, see the [FAQ](faq.md).
