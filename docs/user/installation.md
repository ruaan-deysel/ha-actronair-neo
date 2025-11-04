# Installation Guide

This guide will walk you through the process of installing the ActronAir Neo integration for Home Assistant.

## Prerequisites

Before installing the ActronAir Neo integration, ensure you have:

- A working Home Assistant installation (version 2023.1.0 or newer)
- An ActronAir Neo air conditioning system
- Your ActronAir Neo account credentials (username and password)
- Network connectivity between your Home Assistant instance and the internet

## Installation Methods

There are two ways to install the ActronAir Neo integration:

### Method 1: HACS (Recommended)

The Home Assistant Community Store (HACS) provides an easy way to install and update the integration.

1. Ensure you have [HACS](https://hacs.xyz/) installed on your Home Assistant instance
2. Navigate to HACS in your Home Assistant sidebar
3. Click on "Integrations"
4. Click the "+" button in the bottom right corner
5. Search for "ActronAir Neo"
6. Click on the integration and then click "Download"
7. Restart Home Assistant after the installation is complete

You can also use this button to directly open the repository in HACS:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=ruaan-deysel&repository=ha-actronair-neo&category=integration)

### Method 2: Manual Installation

If you prefer to install the integration manually:

1. Download the latest release from the [GitHub repository](https://github.com/ruaan-deysel/ha-actronair-neo)
2. Extract the contents
3. Copy the `custom_components/actronair_neo` folder to your Home Assistant's `custom_components` directory
4. Restart Home Assistant

```bash
# Example commands for manual installation
cd /tmp
wget https://github.com/ruaan-deysel/ha-actronair-neo/archive/refs/heads/main.zip
unzip main.zip
cp -r ha-actronair-neo-main/custom_components/actronair_neo /path/to/your/homeassistant/custom_components/
```

Replace `/path/to/your/homeassistant/` with the actual path to your Home Assistant configuration directory.

## Verifying Installation

After installation and restarting Home Assistant, you should be able to add the ActronAir Neo integration through the Home Assistant UI:

1. Navigate to Configuration > Integrations
2. Click the "+ ADD INTEGRATION" button
3. Search for "ActronAir Neo"

If the integration appears in the search results, the installation was successful.

## Troubleshooting Installation Issues

If you encounter issues during installation:

- Check the Home Assistant logs for any error messages
- Ensure your Home Assistant version is compatible (2023.1.0 or newer)
- Verify that the integration files are in the correct location
- Make sure you have restarted Home Assistant after installation

For more detailed troubleshooting, see the [Troubleshooting Guide](troubleshooting.md).

## Next Steps

After successful installation, proceed to the [Configuration Guide](configuration.md) to set up your ActronAir Neo integration.
