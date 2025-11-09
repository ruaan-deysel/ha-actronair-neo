# ActronAir Neo Integration for Home Assistant

[![HACS Integration](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub Last Commit](https://img.shields.io/github/last-commit/ruaan-deysel/ha-actronair-neo)](https://github.com/ruaan-deysel/ha-actronair-neo/commits/main)
[![License](https://img.shields.io/github/license/ruaan-deysel/ha-actronair-neo)](./LICENSE)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/ruaan-deysel/ha-actronair-neo)

The ActronAir Neo Integration enables seamless control and monitoring of your ActronAir Neo air conditioning system directly from Home Assistant. With this integration, you can automate climate control, monitor indoor and outdoor temperatures, and adjust settings based on real-time data, all from one central location.

## Features

- **Comprehensive Control**: Easily switch between modes (heat, cool, fan, auto), set temperatures, and adjust fan speeds.
- **Real-time Monitoring**: Keep track of your home's temperature and humidity levels with up-to-date readings.
- **Zone Control**: Manage individual zones in your home for targeted climate control.
- **Automation Friendly**: Integrate ActronAir Neo into your Home Assistant automations to maintain optimal comfort with minimal effort.
- **Periodic Updates**: The system state is automatically refreshed based on your configured interval, ensuring your data is always current.

## Installation

### HACS (Recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=ruaan-deysel&repository=ha-actronair-neo&category=integration)

### Manual

1. Copy the `actronair_neo` folder into your `custom_components` directory.
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

- **Controls**: Main control for your ActronAir Neo system.
- **Sensor**: Temperature and humidity readings.
- **Diagnostics**: System Status, System Health and Filter Status.

The entities will update based on the refresh interval you have configured, providing you with the most recent data.

## Options

You can adjust the following options in the integration settings:

- **Refresh Interval**: How often the integration should fetch updates from the ActronAir Neo API.

## Troubleshooting

If you encounter any issues:

1. Check the [Docs](docs/index.md)
2. Check that your credentials are correct
3. Ensure your ActronAir Neo system is online and accessible
4. Check the Home Assistant logs for any error messages
5. If you encounter a bug, please report it on our [GitHub issues page](https://github.com/ruaan-deysel/ha-actronair-neo/issues)

## Contributing

Contributions to this integration are welcome. Please fork the repository and submit a pull request with your changes.

### Development Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/ruaan-deysel/ha-actronair-neo.git
   cd ha-actronair-neo
   ```

2. Set up a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

### Testing

We encourage adding tests for new features. The test suite can be found in the `tests/` directory.

## License

This integration is released under the MIT License.

## Disclaimer

This integration is not officially associated with or endorsed by ActronAir. ActronAir trademarks belong to ActronAir, and this integration is independently developed.
