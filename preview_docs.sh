#!/bin/bash

# Exit on error
set -e

# Install documentation dependencies if not already installed
if ! command -v mkdocs &> /dev/null; then
    echo "Installing documentation dependencies..."
    pip install -r requirements_docs.txt
fi

# Serve the documentation
echo "Starting documentation server..."
echo "Open http://localhost:8000 in your browser to preview the documentation."
echo "Press Ctrl+C to stop the server."
mkdocs serve
