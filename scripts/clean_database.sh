#!/bin/bash

# Script to clean up unused database tables

# Go to the backend directory
cd "$(dirname "$0")"

# Check if psycopg2 is installed
pip install psycopg2-binary > /dev/null 2>&1

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Run the database cleanup tool
echo "Running database cleanup tool..."
python scripts/clean_database.py

# Deactivate virtual environment if it was activated
if [ -n "$VIRTUAL_ENV" ]; then
    deactivate
fi

echo "Database cleanup process completed." 