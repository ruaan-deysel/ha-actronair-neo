#!/bin/bash

# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run tests with coverage
pytest tests/ -v --cov=custom_components/actronair_neo --cov-report=term-missing

# Return the exit code from pytest
exit $?
