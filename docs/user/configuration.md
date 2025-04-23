# Configuration Guide

This guide will walk you through the process of configuring the ActronAir Neo integration after installation.

## Initial Setup

After installing the ActronAir Neo integration, you need to configure it with your account credentials and system settings.

### Adding the Integration

1. In Home Assistant, navigate to **Configuration** > **Integrations**
2. Click the **+ ADD INTEGRATION** button in the bottom right corner
3. Search for "ActronAir Neo" and select it from the list
4. You will be presented with a configuration form

![Configuration Form](../assets/images/config_form.png)

### Configuration Options

Fill in the following information:

| Field | Description |
|-------|-------------|
| Username | Your ActronAir Neo account username (email address) |
| Password | Your ActronAir Neo account password |
| Update Interval | How often the integration should fetch data from the ActronAir Neo API (in seconds) |
| Enable Zone Control | Toggle to enable or disable zone control functionality |

### Authentication

The integration will attempt to authenticate with the ActronAir Neo API using the provided credentials. If successful, it will discover all available air conditioning systems associated with your account.

### System Selection

If you have multiple ActronAir Neo systems linked to your account, you will be presented with a dropdown menu to select which system you want to add to Home Assistant:

![System Selection](../assets/images/system_selection.png)

Select the system you want to control and click **SUBMIT**. If you want to add multiple systems, you can add the integration again and select a different system each time.

## Advanced Configuration

### Update Interval

The default update interval is set to 60 seconds. You can adjust this based on your needs:

- **Lower interval** (e.g., 30 seconds): More responsive but may hit API rate limits
- **Higher interval** (e.g., 120 seconds): Less responsive but reduces API calls

### Zone Control

If your ActronAir Neo system supports zones, enabling the zone control option will create additional entities for each zone, allowing you to:

- Control temperature settings for individual zones
- Turn zones on or off independently
- Monitor zone-specific temperature and humidity readings

## Reconfiguring the Integration

If you need to change any configuration options after the initial setup:

1. Go to **Configuration** > **Integrations**
2. Find the ActronAir Neo integration and click on it
3. Click the **CONFIGURE** button
4. Update the settings as needed and click **SUBMIT**

## Configuration via YAML

While the integration is primarily configured through the UI, you can also add some advanced options via YAML if needed:

```yaml
# Example configuration.yaml entry
actronair_neo:
  scan_interval: 60
  enable_zone_control: true
```

> **Note**: UI configuration is recommended over YAML configuration for this integration.

## Entities Created

After configuration, the integration will create the following entities:

- **Climate entity**: Main control for your ActronAir Neo system
- **Temperature sensors**: For each zone and the main unit
- **Humidity sensors**: For zones that support humidity readings
- **Binary sensors**: For system status and filter condition
- **Switches**: For enabling/disabling zones

## Next Steps

After configuring the integration, proceed to the [Usage Guide](usage.md) to learn how to control your ActronAir Neo system through Home Assistant.
