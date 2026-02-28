# ActronAir Neo API Explorer

This tool allows you to explore the ActronAir Neo cloud API and understand its responses to assist with development and documentation.

## Features

- Interactive command-line interface for exploring the API
- OAuth 2.0 Device Code Flow authentication (same as the HA integration)
- Auto-loads tokens from the HA integration config entry if available
- View complete device status information
- View event history data (note: Events API disabled by Actron since July 2025)
- Send control commands to your air conditioning system
- Save API responses to JSON files for documentation
- Secure token management (no passwords stored)

## Installation

1. Make sure you have Python 3.7+ installed
2. Clone this repository
3. Create a virtual environment (recommended):

   ```
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. Install the required dependencies:

   ```
   pip install aiohttp aiofiles
   ```

## Usage

Run the script with:

```bash
python actron_neo_explorer.py
```

### Authentication

The tool uses **OAuth 2.0 Device Code Flow** — the same authentication mechanism
as the Home Assistant integration and the `actronneoapi` Python library.

**Token sources** (checked in order):

1. Token file (default: `config/actron_token.json`)
2. HA config entry (from `.storage/core.config_entries`)

If no valid tokens are found, use `--pair` to initiate a new device pairing.

### Command-line Arguments

```
--pair             Initiate OAuth2 Device Code Flow pairing
--status           Print AC status JSON and exit
--events           Print AC events JSON and exit (deprecated API)
-d, --debug        Enable debug logging
-t, --token-file   Path to token file (default: config/actron_token.json)
```

### Available Commands

Once authenticated, you can explore the API with these commands:

1. **Get AC Status** - Retrieves the current status of your AC system
2. **Get AC Events** - Retrieves the event history
3. **Turn AC On** - Sends a command to turn on the AC
4. **Turn AC Off** - Sends a command to turn off the AC
5. **Set Climate Mode** - Change between Cool, Heat, Fan, Auto modes
6. **Set Fan Mode** - Change fan speed settings
7. **Set Temperature** - Change temperature setpoints
8. **Control Zone** - Enable/disable specific zones
9. **Send Custom Command** - Send a custom JSON command
10. **Exit** - Exit the program

### Token Management

The tool securely manages authentication tokens:

- Access and refresh tokens are stored in a local file (default: `config/actron_token.json`)
- Token format uses POSIX timestamps, matching the HA integration format
- Only tokens are stored, never your username or password
- Tokens are automatically refreshed when needed
- Falls back to reading tokens from the HA config entry if the token file is missing
- You can specify a custom token file location with the `-t` option

## API Response Structure

The API responses are documented in `actron_api_structure.md`. This documentation includes:

- The complete JSON structure of API responses
- Field descriptions and data types
- Examples of different commands and responses

## Security Notes

- Device Code Flow means no passwords are handled by this tool
- Authentication tokens are stored locally with limited lifetime
- The tool only communicates with the official ActronAir Neo API
- No data is sent to any third-party services

## Troubleshooting

If you encounter authentication issues:

1. Run with `--pair` to initiate a fresh device pairing
2. Delete the token file (default: `config/actron_token.json`) and pair again
3. Enable debug mode with the `-d` flag for more verbose logging
4. Check if the Events API errors are expected (disabled by Actron since July 2025)

## License

This tool is provided for personal use and to help developers understand the ActronAir Neo API.
