#!/usr/bin/env python
import os
import sys
import django
import random
from collections import defaultdict

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auth_project.settings')
django.setup()

from public_api.models import Dataset, Paper
from django.db.models import Count

def generate_similar_datasets():
    """
    Generate similar dataset relationships based on common categories and papers.
    
    Algorithm:
    1. Clear existing similar_datasets relationships
    2. Group datasets by data_type/category
    3. Find datasets used in the same papers
    4. Combine both approaches to create similar_datasets relationships
    """
    print("Starting similar datasets generation...")
    
    # Get all datasets
    datasets = Dataset.objects.all()
    total_datasets = datasets.count()
    
    if total_datasets == 0:
        print("No datasets found in the database.")
        return
    
    print(f"Found {total_datasets} datasets.")
    
    # Clear existing similar_datasets relationships
    print("Clearing existing similar dataset relationships...")
    for dataset in datasets:
        dataset.similar_datasets.clear()
    
    # Group datasets by data_type/category
    print("Grouping datasets by category...")
    datasets_by_category = defaultdict(list)
    for dataset in datasets:
        category = dataset.data_type or "unknown"
        datasets_by_category[category].append(dataset)
    
    # Find datasets used by the same papers
    print("Finding datasets used by the same papers...")
    paper_datasets = defaultdict(set)
    for paper in Paper.objects.all():
        paper_datasets[paper.id] = set(paper.datasets.all().values_list('id', flat=True))
    
    # Datasets with common papers
    datasets_with_common_papers = defaultdict(set)
    for paper_id, dataset_ids in paper_datasets.items():
        for dataset_id in dataset_ids:
            for other_dataset_id in dataset_ids:
                if dataset_id != other_dataset_id:
                    datasets_with_common_papers[dataset_id].add(other_dataset_id)
    
    # Set similar datasets based on category
    print("Setting similar datasets based on category...")
    for category, category_datasets in datasets_by_category.items():
        if len(category_datasets) > 1:
            for dataset in category_datasets:
                # Get other datasets in the same category
                similar_in_category = [d for d in category_datasets if d.id != dataset.id]
                
                # Add up to 5 similar datasets from the same category
                for similar in random.sample(similar_in_category, min(5, len(similar_in_category))):
                    dataset.similar_datasets.add(similar)
    
    # Add similar datasets based on common papers
    print("Adding similar datasets based on common papers...")
    for dataset in datasets:
        common_paper_datasets = datasets_with_common_papers.get(dataset.id, set())
        if common_paper_datasets:
            # Get the actual dataset objects
            similar_datasets = Dataset.objects.filter(id__in=common_paper_datasets)
            
            # Add up to 3 similar datasets based on common papers
            for similar in similar_datasets[:3]:
                dataset.similar_datasets.add(similar)
    
    # Ensure each dataset has at least some similar datasets
    print("Ensuring each dataset has similar datasets...")
    for dataset in datasets:
        if dataset.similar_datasets.count() == 0:
            # Find random datasets to add as similar
            potential_similar = Dataset.objects.exclude(id=dataset.id).order_by('?')[:3]
            for similar in potential_similar:
                dataset.similar_datasets.add(similar)
    
    # Count total relationships created
    total_relationships = sum(dataset.similar_datasets.count() for dataset in datasets)
    print(f"Process complete! Created {total_relationships} similar dataset relationships.")

if __name__ == "__main__":
    generate_similar_datasets() 