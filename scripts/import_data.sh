#!/bin/bash

# Script to import data into PostgreSQL database

# Set environment variable for PostgreSQL
export USE_POSTGRES=True

# Check if PostgreSQL is running
pg_isready -q
if [ $? -ne 0 ]; then
    echo "PostgreSQL is not running. Please start PostgreSQL before continuing."
    exit 1
fi

# Change to backend directory
cd "$(dirname "$0")"

# Verify that data files exist
if [ ! -f "data/papers_full.json" ] || [ ! -f "data/datasets_full.json" ] || [ ! -f "data/conference.xlsx" ] || [ ! -f "data/scimagojr 2024.csv" ]; then
    echo "Error: Required data files not found in backend/data directory."
    echo "Please ensure the following files exist:"
    echo "  - backend/data/papers_full.json"
    echo "  - backend/data/datasets_full.json"
    echo "  - backend/data/conference.xlsx"
    echo "  - backend/data/scimagojr 2024.csv"
    exit 1
fi

# Check if python dependencies are installed
echo "Checking Python dependencies..."
python -c "import pandas; import tqdm" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing required Python dependencies..."
    pip install pandas openpyxl tqdm
fi

# Run migrations first to ensure tables are created
echo "Running database migrations..."
python manage.py migrate

# Run the import script
echo "Starting data import process..."
python scripts/import_data.py

echo "Data import completed! You can now start the application with:"
echo "    python manage.py runserver" 