# Contributing Guide

Thank you for your interest in contributing to the ActronAir Neo integration for Home Assistant! This guide will help you get started with contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Environment](#development-environment)
- [Development Workflow](#development-workflow)
- [Code Style and Guidelines](#code-style-and-guidelines)
- [Testing](#testing)
- [Documentation](#documentation)
- [Submitting Changes](#submitting-changes)
- [Release Process](#release-process)

## Code of Conduct

This project adheres to the [Home Assistant Community Guidelines](https://www.home-assistant.io/community-guidelines/). By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## Getting Started

### Prerequisites

Before you begin, ensure you have the following installed:
- Python 3.10 or newer
- Git
- A text editor or IDE (VS Code recommended)
- Home Assistant development environment (optional but recommended)

### Fork and Clone the Repository

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/ha-actronair-neo.git
   cd ha-actronair-neo
   ```
3. Add the upstream repository as a remote:
   ```bash
   git remote add upstream https://github.com/ruaan-deysel/ha-actronair-neo.git
   ```

## Development Environment

### Setting Up a Virtual Environment

1. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

2. Activate the virtual environment:
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements_dev.txt
   ```

## Development Workflow

### Creating a Branch

Create a new branch for your changes:
```bash
git checkout -b feature/your-feature-name
```

Use a descriptive branch name that reflects the changes you're making.

### Making Changes

1. Make your changes to the codebase
2. Test your changes to ensure they work as expected

### Keeping Your Branch Updated

Regularly update your branch with changes from upstream:
```bash
git fetch upstream
git rebase upstream/main
```

## Code Style and Guidelines

### Type Annotations

All new code should include type annotations for better code clarity and maintainability.

Example:
```python
def get_temperature(sensor_id: str) -> float:
    """Get the temperature from a sensor.

    Args:
        sensor_id: The ID of the sensor

    Returns:
        The temperature in degrees Celsius
    """
    # Implementation
    return 21.5
```

### Docstrings

All public functions, classes, and methods should have docstrings. We follow the Google docstring style.

Example:
```python
def set_temperature(device_id: str, temperature: float) -> bool:
    """Set the target temperature for a device.
    
    Args:
        device_id: The ID of the device
        temperature: The target temperature in degrees Celsius
        
    Returns:
        True if successful, False otherwise
        
    Raises:
        ValueError: If the temperature is out of range
    """
    # Implementation
    return True
```

### Imports

Organize imports in the following order:
1. Standard library imports
2. Related third-party imports
3. Local application/library specific imports

Use absolute imports for clarity.

### Constants

Constants should be defined at the module level and named in ALL_CAPS.

Example:
```python
DEFAULT_TIMEOUT = 10
MAX_TEMPERATURE = 30.0
MIN_TEMPERATURE = 16.0
```

## Testing

### Running Tests

The test suite can be found in the `tests/` directory. Tests help ensure code quality and prevent regressions.

### Writing Tests

- All new features should include tests
- Tests should be placed in the `tests/` directory
- Test files should be named `test_*.py`
- Use pytest fixtures for common setup
- Mock external dependencies

Example test:
```python
import pytest
from unittest.mock import patch, MagicMock

from custom_components.actronair_neo.api import ActronNeoAPI

@pytest.mark.asyncio
async def test_authenticate_success():
    """Test successful authentication."""
    # Arrange
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json.return_value = {
        "access_token": "test_token",
        "token_type": "bearer",
        "expires_in": 3600
    }
    mock_session.post.return_value.__aenter__.return_value = mock_response
    
    api = ActronNeoAPI("test_user", "test_pass", session=mock_session)
    
    # Act
    result = await api.authenticate()
    
    # Assert
    assert result is True
    assert api._access_token == "test_token"
    assert api._token_type == "bearer"
```

## Documentation

### Updating Documentation

When making changes, update the relevant documentation:
- Update docstrings for any modified code
- Update the README.md if necessary
- Update or add documentation in the docs/ directory

### Building Documentation

If using Sphinx for documentation:
```bash
cd docs
make html
```

## Submitting Changes

### Committing Changes

Make small, focused commits with clear messages:
```bash
git add .
git commit -m "Add feature: detailed description of the change"
```

### Creating a Pull Request

1. Push your branch to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

2. Go to the [original repository](https://github.com/ruaan-deysel/ha-actronair-neo) and create a pull request

3. Fill in the pull request template with:
   - A clear title
   - A description of the changes
   - Any related issues
   - Screenshots if applicable

### Code Review Process

All pull requests will be reviewed by the maintainers. You may be asked to make changes before your pull request is merged.

## Release Process

### Versioning

This project follows [Semantic Versioning](https://semver.org/):
- MAJOR version for incompatible API changes
- MINOR version for new functionality in a backward-compatible manner
- PATCH version for backward-compatible bug fixes

### Changelog

Update the CHANGELOG.md file with your changes under the "Unreleased" section.

### Release Checklist

Before a release:
- Ensure all tests pass
- Update the version number in `manifest.json`
- Update the CHANGELOG.md
- Create a new release on GitHub

## Thank You!

Your contributions help make this integration better for everyone. Thank you for your time and effort!
