# Database Data Import

This directory contains scripts to import data from various sources into the PostgreSQL database for the research assistant application.

## Data Sources

The import system uses the following data files:

1. `backend/data/conference.xlsx` - Contains conference information.
2. `backend/data/scimagojr 2024.csv` - Contains journal information.
3. `backend/data/datasets_full.json` - Contains dataset information.
4. `backend/data/papers_full.json` - Contains paper information.

## Prerequisites

Before running the import script, ensure that:

1. PostgreSQL is installed and running
2. You have the required Python packages installed:
   - pandas
   - openpyxl (for Excel file reading)
   - tqdm (for progress bars)

## Running the Import

To import the data into the PostgreSQL database:

1. Make sure PostgreSQL is running.
2. Navigate to the backend directory.
3. Run the import script:

```bash
./import_data.sh
```

Alternatively, you can run the Python script directly:

```bash
# Set environment variable for PostgreSQL
export USE_POSTGRES=True

# Run migrations
python manage.py migrate

# Run the import script
python scripts/import_data.py
```

## What Gets Imported

The import script:

1. Creates a default admin user if one doesn't exist
2. Imports datasets from `datasets_full.json`
3. Imports papers from `papers_full.json`
4. Creates connections between papers and datasets based on the data
5. Creates publications (journal entries) by matching papers to journal names
6. Adds conference information to papers based on conference names

## Data Relationships

The import process maintains the following relationships:

- Papers <-> Datasets: Through the DatasetReference model
- Papers <-> Conferences: Direct field in the Paper model
- Papers <-> Journals: Through the Publication model

## Troubleshooting

If you encounter issues:

1. Ensure PostgreSQL is running (`pg_isready -q`)
2. Verify all data files exist in the correct location
3. Check the database connection settings in `auth_project/settings.py`
4. Make sure you have the required Python dependencies installed

## Manual Data Entry

If specific data is missing, the script will generate fake placeholder data:

- DOIs are generated as `10.1000/paper{i}`
- If conferences are not found, default conference data is used
- If journals are not found, default journal data is used

You can manually edit data in the Django admin interface after import. 