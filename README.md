
# ActronAir Neo Integration for Home Assistant

> **IMPORTANT NOTICE:** This integration is currently under active development. It may contain bugs or incomplete features. Use at your own risk and please report any issues you encounter.

The ActronAir Neo Integration enables seamless control and monitoring of your ActronAir Neo air conditioning system directly from Home Assistant. With this integration, you can automate climate control, monitor indoor and outdoor temperatures, and adjust settings based on real-time data, all from one central location.

## Development Status

This integration is in active development. Here are a few things to keep in mind:

- Features may be added, changed, or removed without notice.
- There might be bugs or unexpected behavior.
- Regular updates may be necessary as the integration evolves.
- Feedback and contributions are welcome to help improve the integration.

## Features

- **Comprehensive Control**: Easily switch between modes (heat, cool, fan, auto), set temperatures, and adjust fan speeds.
- **Real-time Monitoring**: Keep track of your home's temperature and humidity levels with up-to-date readings.
- **Automation Friendly**: Integrate ActronAir Neo into your Home Assistant automations to maintain optimal comfort with minimal effort.
- **Periodic Updates**: The system state is automatically refreshed based on your configured interval, ensuring your data is always current.

## Installation

### HACS (Recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Domalab&repository=https%3A%2F%2Fgithub.com%2Fdomalab%2Fha-actronair-neo&category=Integration)

### Manual

1. Copy the `actron_air_neo` folder into your `custom_components` directory.
2. Restart Home Assistant.

## Configuration

1. In Home Assistant, go to Configuration > Integrations.
2. Click the "+ ADD INTEGRATION" button.
3. Search for "ActronAir Neo" and select it.
4. Enter your ActronAir Neo username and password.
5. Follow the prompts to complete the setup.

## Usage

After setup, your ActronAir Neo system will appear as a climate entity in Home Assistant. You can control it from the Home Assistant frontend or include it in your automations.

## Entities

- **Climate**: Main control for your ActronAir Neo system.
- **Sensor**: Temperature and humidity readings.

The entities will update based on the refresh interval you have configured, providing you with the most recent data.

## Options

You can adjust the following options in the integration settings:

- **Refresh Interval**: How often the integration should fetch updates from the ActronAir Neo API.

## Troubleshooting

If you encounter any issues:

1. Check that your credentials are correct.
2. Ensure your ActronAir Neo system is online and accessible.
3. Check the Home Assistant logs for any error messages.
4. If you encounter a bug, please report it on our [GitHub issues page](https://github.com/domalab/ha-actronair-neo/issues).

## Contributing

Contributions to this integration are welcome. Please fork the repository and submit a pull request with your changes. Make sure to follow the contribution guidelines.

## License

This integration is released under the Apache License.

## Disclaimer

This integration is not officially associated with or endorsed by ActronAir. ActronAir trademarks belong to ActronAir, and this integration is independently developed.
