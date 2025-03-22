# ActronAir Neo API Explorer

This tool allows you to explore the ActronAir Neo cloud API and understand its responses to assist with development and documentation.

## Features

- Interactive command-line interface for exploring the API
- Authentication with ActronAir Neo cloud services
- View complete device status information
- View event history data
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

The tool will prompt you for your ActronAir Neo username and password. These credentials are only used to authenticate with the ActronAir Neo API and are never stored locally.

You can also provide credentials via command-line arguments:

```bash
python actron_neo_explorer.py -u your_username -p your_password
```

### Command-line Arguments

```
-u, --username     ActronAir Neo account username
-p, --password     ActronAir Neo account password
-d, --debug        Enable debug logging
-t, --token-file   Path to token file (default: actron_token.json in script directory)
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
0. **Exit** - Exit the program

### Token Management

The tool securely manages authentication tokens:

- Access and refresh tokens are stored in a local file (default: `actron_token.json`)
- Only tokens are stored, never your username or password
- Tokens are automatically refreshed when needed
- You can specify a custom token file location with the `-t` option

## API Response Structure

The API responses are documented in `actron_api_structure.md`. This documentation includes:

- The complete JSON structure of API responses
- Field descriptions and data types
- Examples of different commands and responses

## Security Notes

- Your username and password are only used for authentication and are never stored
- Authentication tokens are stored locally with limited lifetime
- The tool only communicates with the official ActronAir Neo API
- No data is sent to any third-party services

## Troubleshooting

If you encounter authentication issues:

1. Verify your ActronAir Neo account credentials
2. Delete the token file (default: `actron_token.json`) and try again
3. Enable debug mode with the `-d` flag for more verbose logging
4. Check if your IP is blocked due to too many authentication attempts

## License

This tool is provided for personal use and to help developers understand the ActronAir Neo API.
