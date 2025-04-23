# Importing Venue Data (Journals and Conferences)

This Django management command allows you to import journal and conference data from files in the `backend/data/` directory.

## Data Files

The command reads data from two files:

1. **Journal data**: `backend/data/scimagojr 2024.csv`
   - This CSV file contains journal information including names, impact factors, quartiles, and publishers

2. **Conference data**: `backend/data/era2010_conference_list.xlsx`
   - This Excel file contains conference information including names, acronyms, and rankings

## Command Usage

To import the venue data, run:

```bash
python manage.py import_venues_data
```

### Options

- `--delete-existing`: Delete all existing journal and conference records before importing
  ```bash
  python manage.py import_venues_data --delete-existing
  ```

## Data Model

The data is imported into two Django models:

### Journal Model

Fields populated from the CSV file:
- `name`: Journal name
- `impact_factor`: SJR impact factor (numeric value)
- `quartile`: Best quartile rating (Q1, Q2, etc.)
- `publisher`: Publisher name
- `abbreviation`: ISSN number

### Conference Model

Fields populated from the Excel file:
- `name`: Conference name
- `abbreviation`: Conference acronym
- `rank`: Conference ranking

## Example

```bash
# Run the command with output
$ python manage.py import_venues_data

Importing journals from backend/data/scimagojr 2024.csv...
Successfully imported 28970 journals (12 skipped)
Importing conferences from backend/data/era2010_conference_list.xlsx...
Successfully imported 1743 conferences (5 skipped)
```

## Notes

- The command uses transactions to ensure data integrity during import
- Existing records with the same name will be updated with new data
- Records with empty names will be skipped 