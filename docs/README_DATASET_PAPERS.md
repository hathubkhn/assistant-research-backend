# Dataset Papers Relationship Manager

## Overview

This README explains how the relationship between `Dataset` and `Paper` models is managed in the system, particularly focusing on the migration from using a JSON field to a proper many-to-many relationship.

## Database Structure

The system has two main models:

1. **Dataset Model**
   - Contains information about datasets
   - Has a `dataset_papers` JSONField that stores paper data as a JSON array
   - Has a many-to-many relationship with the Paper model through the `papers` field

2. **Paper Model**
   - Contains information about research papers
   - Has a many-to-many relationship with the Dataset model through the `datasets` field

3. **Dataset-Papers Relationship**
   - The relationship is stored in the `public_api_dataset_papers` table
   - This is a standard Django many-to-many join table with:
     - `dataset_id`: Foreign key to the Dataset model
     - `paper_id`: Foreign key to the Paper model

## Migration Process

The `process_dataset_papers.py` script handles the migration from the JSON field to the proper relationship:

1. Checks if necessary database tables exist
2. For each dataset with a `dataset_papers` JSON field:
   - Parses the JSON data
   - For each paper in the JSON:
     - Checks if the paper already exists in the database (by title)
     - If it exists, uses the existing paper
     - If it doesn't exist, creates a new paper record
     - Creates a relationship between the dataset and paper

## How to Run

To process all dataset-paper relationships:

```bash
cd backend
python process_dataset_papers.py
```

The script will:
1. Report the initial number of relationships
2. Process all datasets with the `dataset_papers` field
3. Create missing papers and relationships
4. Report a summary of actions taken

## API Changes

The `dataset_detail` API endpoint (/api/datasets/{id}/) has been updated to:
1. Return all related papers from the many-to-many relationship
2. Include more detailed paper information including:
   - Abstract
   - Keywords
   - DOI
   - Download URL
   - Venue type (journal/conference)

## UI Changes

The dataset detail page in the frontend has been enhanced to:
1. Display more comprehensive paper information
2. Show paper abstracts (truncated)
3. Display keywords as tags
4. Add links to paper PDFs and DOIs when available
5. Distinguish between journal and conference papers

## Maintenance

To maintain this relationship:
1. Always use the many-to-many relationship (`dataset.papers.add(paper)`) to create new relationships
2. Don't directly modify the `dataset_papers` JSON field
3. If you need to update the relationships in bulk, use the provided script as a reference 