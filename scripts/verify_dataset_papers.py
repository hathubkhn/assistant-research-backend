#!/usr/bin/env python
import os
import json
import random

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auth_project.settings')
import django
django.setup()

from public_api.models import Dataset, Paper
from django.db import connection

def verify_dataset_papers():
    """Verify that dataset-paper relationships are properly set up"""
    
    # Get count of datasets and papers
    dataset_count = Dataset.objects.count()
    paper_count = Paper.objects.count()
    
    print(f"Total datasets: {dataset_count}")
    print(f"Total papers: {paper_count}")
    
    # Check the relationship table
    with connection.cursor() as cursor:
        cursor.execute('SELECT COUNT(*) FROM public_api_dataset_papers')
        relation_count = cursor.fetchone()[0]
        
        print(f"\nTotal dataset-paper relationships: {relation_count}")
        
        # Get some statistics
        cursor.execute('''
            SELECT COUNT(DISTINCT dataset_id) 
            FROM public_api_dataset_papers
        ''')
        datasets_with_papers = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(DISTINCT paper_id) 
            FROM public_api_dataset_papers
        ''')
        papers_with_datasets = cursor.fetchone()[0]
        
        print(f"Datasets with at least one paper: {datasets_with_papers} ({datasets_with_papers/dataset_count*100:.2f}%)")
        print(f"Papers linked to at least one dataset: {papers_with_datasets} ({papers_with_datasets/paper_count*100:.2f}%)")
    
    # Sample check - get 5 random datasets and show their papers
    sample_size = min(5, dataset_count)
    sample_datasets = random.sample(list(Dataset.objects.all()), sample_size)
    
    print(f"\nSample of {sample_size} datasets and their papers:")
    
    for dataset in sample_datasets:
        paper_count = dataset.papers.count()
        print(f"\nDataset: {dataset.name}")
        print(f"Paper count from relationship: {paper_count}")
        
        # Check JSON field if it exists
        if dataset.dataset_papers:
            if isinstance(dataset.dataset_papers, str):
                try:
                    papers_data = json.loads(dataset.dataset_papers)
                except:
                    papers_data = []
            else:
                papers_data = dataset.dataset_papers
                
            print(f"Paper count from JSON field: {len(papers_data)}")
            
            # Show sample of papers (max 3)
            if paper_count > 0:
                print("\nSample papers:")
                for paper in dataset.papers.all()[:3]:
                    print(f"  - {paper.title[:60]}...")
        
        # Verify if dataset_papers JSON entries are properly linked
        if dataset.dataset_papers and paper_count > 0:
            # Check a random paper from the relationship to see if it matches one in the JSON
            paper = random.choice(list(dataset.papers.all()))
            
            # Try to find this paper title in the JSON data
            paper_found = False
            if isinstance(dataset.dataset_papers, (list, tuple)):
                for paper_data in dataset.dataset_papers:
                    if isinstance(paper_data, dict) and paper_data.get('title') == paper.title:
                        paper_found = True
                        break
            
            if paper_found:
                print(f"\nVerification: Found paper '{paper.title[:30]}...' in both the relationship and JSON")
            else:
                print(f"\nVerification: Paper '{paper.title[:30]}...' in relationship but NOT found in JSON")

if __name__ == "__main__":
    verify_dataset_papers() 