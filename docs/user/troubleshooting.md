# Troubleshooting Guide

This guide helps you diagnose and resolve common issues with the ActronAir Neo integration.

## Common Issues and Solutions

### Connection Problems

#### Issue: Integration Cannot Connect to ActronAir Neo API

**Symptoms:**
- Error message during setup: "Cannot connect to ActronAir Neo API"
- Integration shows as "Unavailable" in Home Assistant

**Possible Causes and Solutions:**

1. **Incorrect Credentials**
   - Double-check your username and password
   - Try logging in to the ActronAir Neo mobile app to verify credentials
   - Reset your password if necessary

2. **Network Issues**
   - Ensure your Home Assistant instance has internet access
   - Check if your network has any firewall rules blocking outbound connections
   - Try restarting your network equipment

3. **API Rate Limiting**
   - The ActronAir Neo API has rate limits that may temporarily block access
   - Increase the update interval in the integration configuration
   - Wait 15-30 minutes and try again

4. **ActronAir Neo Service Outage**
   - Check if the ActronAir Neo service is experiencing an outage
   - Wait for the service to be restored

### Entity Issues

#### Issue: Missing Entities

**Symptoms:**
- Some expected entities are not appearing in Home Assistant
- Zone entities are missing

**Possible Causes and Solutions:**

1. **Zone Control Not Enabled**
   - Ensure "Enable Zone Control" is toggled on in the integration configuration
   - Reconfigure the integration to enable zone control

2. **Unsupported Features**
   - Your ActronAir Neo model may not support all features
   - Check your model's specifications for supported features

3. **Entity Registry Issues**
   - Check if entities are hidden in the entity registry
   - Go to Configuration > Entities and search for "actronair"
   - Unhide any hidden entities

#### Issue: Entities Show as "Unavailable"

**Symptoms:**
- Entities appear in Home Assistant but show as "Unavailable"
- Controls don't work

**Possible Causes and Solutions:**

1. **Communication Issues**
   - Check if the integration can communicate with the ActronAir Neo API
   - Look for error messages in the Home Assistant logs
   - Restart the integration

2. **System Offline**
   - Verify that your ActronAir Neo system is powered on and connected to the internet
   - Check the system status in the ActronAir Neo mobile app

### Control Problems

#### Issue: Cannot Control System

**Symptoms:**
- Commands sent from Home Assistant don't affect the actual system
- Temperature or mode changes don't take effect

**Possible Causes and Solutions:**

1. **Permission Issues**
   - Ensure your ActronAir Neo account has permission to control the system
   - Check if multiple accounts are trying to control the system simultaneously

2. **System in Special Mode**
   - The system may be in a special mode (e.g., service mode, firmware update)
   - Check the system status and wait for the special mode to complete

3. **Command Conflicts**
   - Multiple automations or scripts may be sending conflicting commands
   - Review your automations and scripts for potential conflicts

4. **API Limitations**
   - Some commands may not be supported by the API
   - Check the API documentation for supported commands

## Diagnostic Steps

### Checking Logs

Home Assistant logs can provide valuable information for troubleshooting:

1. Navigate to **Configuration** > **Logs**
2. Set the log level to "Debug" temporarily
3. Search for "actronair_neo" to find relevant log entries
4. Look for error messages or warnings

Alternatively, you can check the logs via the command line:

```bash
grep -i "actronair_neo" ~/.homeassistant/home-assistant.log
```

### Testing API Connectivity

You can test connectivity to the ActronAir Neo API using curl:

```bash
curl -I https://nimbus.actronair.com.au/api/v0/client/ac-systems
```

A successful response should return HTTP status 200 or 401 (unauthorized).

### Restarting the Integration

Sometimes restarting the integration can resolve issues:

1. Go to **Configuration** > **Integrations**
2. Find the ActronAir Neo integration
3. Click the three dots menu (⋮)
4. Select **Reload**

If reloading doesn't help, try removing and re-adding the integration.

## Advanced Troubleshooting

### Enabling Debug Logging

You can enable debug logging for the integration by adding the following to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.actronair_neo: debug
```

Restart Home Assistant after making this change.

### Checking API Responses

For advanced users, you can examine the raw API responses:

1. Enable debug logging as described above
2. Trigger an update by changing a setting
3. Check the logs for API request and response details
4. Look for any error codes or unexpected values

### Reporting Issues

If you've tried the troubleshooting steps and still have issues:

1. Gather relevant information:
   - Home Assistant version
   - ActronAir Neo integration version
   - Error messages from logs
   - Steps to reproduce the issue

2. Report the issue on GitHub:
   - Go to the [GitHub Issues page](https://github.com/ruaan-deysel/ha-actronair-neo/issues)
   - Click "New Issue"
   - Provide a clear description and the information gathered above

## Next Steps

If you're still experiencing issues after trying these troubleshooting steps, check the [FAQ](faq.md) for more information or reach out to the community for help.
