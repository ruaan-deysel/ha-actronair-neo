# Frequently Asked Questions (FAQ)

This document answers common questions about the ActronAir Neo integration for Home Assistant.

## General Questions

### What is the ActronAir Neo integration?

The ActronAir Neo integration allows you to control and monitor your ActronAir Neo air conditioning system through Home Assistant. It connects to the ActronAir Neo cloud API to provide seamless control of your system.

### Which ActronAir models are supported?

This integration supports all ActronAir Neo models that can connect to the ActronAir Neo cloud service. This includes:
- ActronAir Neo Series
- ActronAir Que Series (with Neo connectivity)
- Other ActronAir models with Neo connectivity

### Is this an official ActronAir integration?

No, this integration is not officially associated with or endorsed by ActronAir. It is a community-developed integration that interacts with the ActronAir Neo API.

### Does this integration work without internet?

No, this integration requires internet connectivity as it communicates with the ActronAir Neo cloud API. If your internet connection is down, the integration will not be able to control your system.

## Setup and Configuration

### Why can't I find the integration in the Home Assistant integration list?

If you can't find the integration after installation, try the following:
1. Make sure you've restarted Home Assistant after installation
2. Check that the integration files are in the correct location
3. Clear your browser cache and reload the Home Assistant web interface
4. Search for "ActronAir" (without "Neo") as it might be listed that way

### How often does the integration update data from my system?

By default, the integration updates data every 60 seconds. You can adjust this interval in the integration configuration settings. A shorter interval provides more responsive updates but may hit API rate limits.

### Can I control multiple ActronAir Neo systems?

Yes, if you have multiple systems linked to your ActronAir Neo account, the integration will detect them during setup and allow you to select which system to add. You can add each system separately to Home Assistant by adding the integration multiple times and selecting a different system each time.

### Why are some zones not appearing?

If you have zones that aren't appearing in Home Assistant:
1. Make sure "Enable Zone Control" is toggled on in the integration configuration
2. Verify that the zones are properly configured in your ActronAir Neo system
3. Some zones might be disabled at the system level

## Features and Functionality

### Can I control individual zone temperatures?

Yes, if your ActronAir Neo system supports zone temperature control, you can set different target temperatures for each zone. Each zone will have its own climate entity in Home Assistant.

### Does the integration support schedules?

The integration itself doesn't implement scheduling, but you can create schedules using Home Assistant's automation system. See the [Usage Guide](usage.md) for examples of scheduling automations.

### Can I see energy usage statistics?

Currently, the integration doesn't provide energy usage statistics. This feature may be added in future updates if the ActronAir Neo API provides this data.

### Does the integration support away mode?

Yes, if your ActronAir Neo system supports away mode, you can control it through the integration. Away mode appears as an option in the climate entity.

### Can I control the system with voice assistants?

Yes, since the integration creates standard Home Assistant climate entities, you can control your ActronAir Neo system with any voice assistant that integrates with Home Assistant, such as Google Assistant, Amazon Alexa, or Apple HomeKit.

## Troubleshooting

### Why does the integration show "Unavailable" after working fine?

This usually indicates a connection issue. Possible causes include:
1. Internet connectivity problems
2. ActronAir Neo cloud service outage
3. API rate limiting
4. Authentication token expiration

See the [Troubleshooting Guide](troubleshooting.md) for more detailed solutions.

### Why are temperature changes not taking effect?

If temperature changes made in Home Assistant aren't affecting your actual system:
1. Check if the system is in a mode that accepts temperature changes (e.g., not in Fan Only mode)
2. Verify that the temperature is within the allowed range for your system
3. Check if there are any conflicts with the system's built-in scheduling
4. Look for error messages in the Home Assistant logs

### How do I fix "Authentication Failed" errors?

If you're seeing authentication errors:
1. Verify your username and password are correct
2. Try logging out and back in to the ActronAir Neo mobile app
3. Remove and re-add the integration in Home Assistant
4. Check if your ActronAir Neo account has any security restrictions

### The integration is using too many API calls. How can I reduce them?

To reduce API calls:
1. Increase the update interval in the integration configuration
2. Limit the number of automations that control the system
3. Use the state of the climate entity for conditions rather than repeatedly polling sensors

## Advanced Usage

### Can I access raw API data from the system?

Yes, the integration stores the raw API data in the coordinator. Advanced users can access this data for custom templates or scripts. The data is available in the `coordinator.data.raw_data` attribute.

### How can I contribute to the integration?

Contributions are welcome! See the [Contributing Guide](../developer/contributing.md) for information on how to contribute to the integration.

### Can I use this integration with MQTT?

The integration doesn't use MQTT directly, but you can create MQTT entities that mirror the state of the ActronAir Neo entities using Home Assistant's MQTT integration and automations.

### Is there an API documentation for developers?

Yes, see the [API Reference](../api/authentication.md) for detailed information about the ActronAir Neo API and how the integration interacts with it.

## Still Have Questions?

If your question isn't answered here, check the [Troubleshooting Guide](troubleshooting.md) or open an issue on the [GitHub repository](https://github.com/ruaan-deysel/ha-actronair-neo/issues).
