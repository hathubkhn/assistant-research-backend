#!/usr/bin/env python
import os
import json
import uuid

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auth_project.settings')
import django
django.setup()

from public_api.models import Dataset, Paper
from django.db import connection, transaction

def check_tables():
    """Check if necessary tables exist"""
    with connection.cursor() as cursor:
        # Check if public_api_dataset_papers exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'public_api_dataset_papers'
            )
        """)
        dataset_papers_exists = cursor.fetchone()[0]
        
        # Check if public_api_paper exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'public_api_paper'
            )
        """)
        paper_exists = cursor.fetchone()[0]
        
        return dataset_papers_exists, paper_exists

def get_current_relationships():
    """Get count of existing relationships"""
    with connection.cursor() as cursor:
        if check_tables()[0]:  # If dataset_papers table exists
            cursor.execute('SELECT COUNT(*) FROM public_api_dataset_papers')
            return cursor.fetchone()[0]
        return 0

def process_dataset_papers():
    """Process dataset_papers JSON field and create proper relationships"""
    # Get counts before processing
    initial_count = get_current_relationships()
    print(f"Initial dataset-paper relationships: {initial_count}")
    
    # Get count of datasets with dataset_papers field
    datasets_with_papers = 0
    total_papers_to_process = 0
    
    for dataset in Dataset.objects.all():
        if dataset.dataset_papers:
            datasets_with_papers += 1
            papers_data = dataset.dataset_papers
            if isinstance(papers_data, str):
                try:
                    papers_data = json.loads(papers_data)
                except:
                    papers_data = []
            
            total_papers_to_process += len(papers_data)
    
    print(f"Found {datasets_with_papers} datasets with dataset_papers field")
    print(f"Total papers to process: {total_papers_to_process}")
    
    # Process each dataset
    papers_processed = 0
    relationships_created = 0
    new_papers_created = 0
    
    with transaction.atomic():
        for dataset in Dataset.objects.all():
            if not dataset.dataset_papers:
                continue
            
            # Parse dataset_papers JSON field
            try:
                papers_data = dataset.dataset_papers
                if isinstance(papers_data, str):
                    try:
                        papers_data = json.loads(papers_data)
                    except:
                        papers_data = []
                
                print(f"Processing dataset: {dataset.name} - {len(papers_data)} papers")
                
                # Process each paper entry
                for paper_data in papers_data:
                    papers_processed += 1
                    
                    # Try to find existing paper by title
                    title = paper_data.get('title')
                    if not title:
                        print(f"  Skipping paper without title")
                        continue
                    
                    # First check if the paper already exists
                    existing_papers = Paper.objects.filter(title=title)
                    
                    if existing_papers.exists():
                        # Use existing paper
                        paper = existing_papers.first()
                        print(f"  Found existing paper: {paper.title[:50]}...")
                    else:
                        # Create new paper
                        authors = paper_data.get('authors', [])
                        if isinstance(authors, str):
                            try:
                                authors = json.loads(authors)
                            except:
                                authors = [authors]
                        
                        # Extract year, defaulting to current year if not available
                        try:
                            year = int(paper_data.get('year', 2023))
                        except:
                            year = 2023
                        
                        # Create a new paper record
                        paper = Paper.objects.create(
                            id=uuid.uuid4(),
                            title=title,
                            authors=authors,
                            abstract=paper_data.get('abstract', ''),
                            conference=paper_data.get('conference', ''),
                            year=year,
                            field=paper_data.get('field', ''),
                            downloadUrl=paper_data.get('downloadUrl', ''),
                            doi=paper_data.get('doi', '')
                        )
                        new_papers_created += 1
                        print(f"  Created new paper: {paper.title[:50]}...")
                    
                    # Add relationship between dataset and paper if not already exists
                    if not dataset.papers.filter(id=paper.id).exists():
                        dataset.papers.add(paper)
                        relationships_created += 1
                        print(f"  Added relationship: {dataset.name} -> {paper.title[:30]}...")
                
            except Exception as e:
                print(f"Error processing dataset {dataset.name}: {str(e)}")
    
    # Get counts after processing
    final_count = get_current_relationships()
    
    print("\nProcessing summary:")
    print(f"Papers processed: {papers_processed}")
    print(f"New papers created: {new_papers_created}")
    print(f"New relationships created: {relationships_created}")
    print(f"Initial relationship count: {initial_count}")
    print(f"Final relationship count: {final_count}")
    print(f"Net change: {final_count - initial_count}")

if __name__ == "__main__":
    dataset_papers_exists, paper_exists = check_tables()
    
    if not paper_exists:
        print("Error: public_api_paper table does not exist!")
        exit(1)
    
    if not dataset_papers_exists:
        print("Note: public_api_dataset_papers table doesn't exist. It will be created automatically by Django's ORM.")
    
    # Run the processing
    process_dataset_papers() 