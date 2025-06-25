#!/usr/bin/env python
import os
import json
import uuid
import random

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auth_project.settings')
import django
django.setup()

from public_api.models import Dataset, Paper
from django.db import connection, transaction

def process_dataset_sample():
    """Process a sample of datasets for testing"""
    
    # Get a sample of datasets with dataset_papers content
    datasets_with_papers = []
    for dataset in Dataset.objects.all():
        if dataset.dataset_papers and not dataset.papers.exists():
            datasets_with_papers.append(dataset)
            if len(datasets_with_papers) >= 5:  # Process just 5 datasets
                break
    
    if not datasets_with_papers:
        print("No suitable datasets found for testing")
        return
    
    print(f"Found {len(datasets_with_papers)} datasets for sample processing")
    
    # Process each dataset
    with transaction.atomic():
        for dataset in datasets_with_papers:
            papers_data = dataset.dataset_papers
            if isinstance(papers_data, str):
                try:
                    papers_data = json.loads(papers_data)
                except:
                    papers_data = []
            
            print(f"\nProcessing dataset: {dataset.name} - {len(papers_data)} papers")
            
            # Process just up to 10 papers for each dataset
            sample_papers = papers_data[:10] if len(papers_data) > 10 else papers_data
            
            for paper_data in sample_papers:
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
                    print(f"  Created new paper: {paper.title[:50]}...")
                
                # Add relationship between dataset and paper if not already exists
                if not dataset.papers.filter(id=paper.id).exists():
                    dataset.papers.add(paper)
                    print(f"  Added relationship: {dataset.name} -> {paper.title[:30]}...")
    
    # Verify the sample processed correctly
    print("\nVerification of processed datasets:")
    for dataset in datasets_with_papers:
        paper_count = dataset.papers.count()
        print(f"Dataset: {dataset.name} - Papers: {paper_count}")
        if paper_count > 0:
            print("  Sample papers:")
            for paper in dataset.papers.all()[:3]:
                print(f"  - {paper.title[:60]}...")

if __name__ == "__main__":
    process_dataset_sample() 