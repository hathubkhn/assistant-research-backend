#!/bin/bash

# Check if the USE_POSTGRES environment variable is set
if [ -z "$USE_POSTGRES" ]; then
    # If not set, use PostgreSQL by default
    export USE_POSTGRES=True
fi

# Activate the virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the development server
python manage.py runserver 0.0.0.0:8000 