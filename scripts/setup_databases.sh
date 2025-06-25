#!/bin/bash

# Script to set up both research_asssistant_db and auth_db databases and sync users

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "PostgreSQL is not installed. Please install it before continuing."
    exit 1
fi

# Create research_asssistant_db if it doesn't exist
echo "Creating research_asssistant_db database..."
createdb research_asssistant_db 2>/dev/null || echo "Database research_asssistant_db already exists"

# Create auth_db if it doesn't exist
echo "Creating auth_db database..."
createdb auth_db 2>/dev/null || echo "Database auth_db already exists"

# Set environment variable for PostgreSQL
export USE_POSTGRES=True

# Apply migrations to both databases
echo "Applying migrations to research_asssistant_db..."
python manage.py migrate --database=default

echo "Applying migrations to auth_db..."
python manage.py migrate --database=auth_db

# Sync users between databases
echo "Syncing users between databases..."
python manage.py sync_users

# Import sample research papers and datasets
echo "Importing sample research papers and datasets..."
python manage.py import_sample_data

echo "Database setup completed successfully!"
echo "To run the server with PostgreSQL, use: export USE_POSTGRES=True && python manage.py runserver" 