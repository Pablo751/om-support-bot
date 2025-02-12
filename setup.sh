# setup.sh
#!/bin/bash

# Exit on error
set -e

echo "Setting up YOM Support Bot..."

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p data logs

# Copy environment file if it doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file from template. Please update it with your credentials."
fi

# Create test data directory
mkdir -p src/tests/data