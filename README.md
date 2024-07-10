# Work In Progress - Work In Progress - Actron Air Neo Home Assistant Integration

This is a custom component for Home Assistant that integrates with the Actron Air Neo HVAC system.

## Installation

### HACS Installation

1. Ensure you have [HACS](https://hacs.xyz) installed.
2. Add this repository to HACS as a custom repository:
    ```bash
    https://github.com/domalab/ha-actronair-neo
    ```
3. Search for "Actron Air Neo" in HACS and install it.

### Manual Installation

1. Clone this repository into your Home Assistant `custom_components` directory:
    ```bash
    git clone https://github.com/domalab/ha-actronair-neo.git
    ```
2. Move the `actron_air_neo` directory to the `custom_components` directory in your Home Assistant configuration:
    ```bash
    mv actron_air_neo_home_assistant/custom_components/actron_air_neo custom_components/
    ```

## Configuration

1. Navigate to Configuration > Integrations in Home Assistant.
2. Click on "Add Integration" and search for "Actron Air Neo".
3. Follow the prompts to enter your Actron Neo credentials.

## Usage

- **Temperature Control**: You can set the desired temperature for each zone.
- **Mode Control**: You can switch between HVAC modes (e.g., heat, cool, off).
- **Zone Control**: You can turn individual zones on or off.