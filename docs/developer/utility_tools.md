# Utility Tools

This page documents the utility tools included in the `utils/` directory of the ActronAir Neo integration. These tools are designed to help developers understand the ActronAir Neo API, troubleshoot issues, and generate diagnostic information.

## ActronAir Neo API Explorer

The API Explorer is a command-line tool that allows you to interact with the ActronAir Neo API directly, view responses, and send commands to your air conditioning system.

![API Explorer](../assets/images/api_explorer.png)

### Features

- Interactive command-line interface for exploring the API
- Authentication with ActronAir Neo cloud services
- View complete device status information
- View event history data
- Send control commands to your air conditioning system
- Save API responses to JSON files for documentation
- Secure token management (no passwords stored)
- Generate diagnostic reports

### Installation

1. Make sure you have Python 3.7+ installed
2. Clone the repository
3. Create a virtual environment (recommended):

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. Install dependencies:

   ```bash
   pip install aiohttp aiofiles
   ```

5. Optional: Install Rich for a better UI experience:

   ```bash
   pip install rich
   ```

### Usage

Run the script with:

```bash
python utils/actron_neo_explorer.py
```

#### Command-line Arguments

```
-u, --username     ActronAir Neo account username
-p, --password     ActronAir Neo account password
-d, --debug        Enable debug logging
-t, --token-file   Path to token file (default: actron_token.json)
-g, --generate-diagnostics Generate diagnostics.md file
--docs             Show API documentation structure
```

#### Available Commands

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
D. **Generate Diagnostics** - Create a diagnostics.md file with system information

### Security Notes

- Your username and password are only used for authentication and are never stored
- Authentication tokens are stored locally with limited lifetime
- The tool only communicates with the official ActronAir Neo API
- No data is sent to any third-party services

## API Documentation Files

The utils directory also contains detailed documentation about the ActronAir Neo API structure:

### actron_api_structure.md

This file documents the structure of the ActronAir Neo API responses, including:

- Authentication endpoints and responses
- Device information structure
- Status API response format
- Events API response format
- Command structure for controlling the system
- Error response formats

You can view this documentation directly by running:

```bash
python utils/actron_neo_explorer.py --docs
```

### ActronAirNeoAPI.md

This file provides a cheat sheet for the ActronAir Neo API, including:

- Authentication process
- API endpoints
- Request and response formats
- Command examples

## Generating Diagnostics

The API Explorer includes a feature to generate a diagnostics report about your ActronAir Neo system. This can be helpful when troubleshooting issues or when providing information for bug reports.

To generate a diagnostics report:

```bash
python utils/actron_neo_explorer.py -g
```

This will create a `diagnostics.md` file in the project root with detailed information about your system, including:

- System model and serial number
- Connected zones and sensors
- Current system status
- User settings
- System capabilities

## Using the Tools for Development

These tools are particularly useful when:

1. **Implementing new features** - Understand the API structure and test commands
2. **Debugging issues** - Verify API responses and system behavior
3. **Creating documentation** - Generate accurate API documentation
4. **Troubleshooting** - Generate diagnostic reports for support

## Contributing to the Tools

If you'd like to improve these utility tools:

1. Fork the repository
2. Make your changes
3. Submit a pull request with a clear description of your improvements

Please ensure any contributions maintain the security principles of the original tools, particularly regarding credential handling.
