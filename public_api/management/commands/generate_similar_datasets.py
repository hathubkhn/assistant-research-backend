from django.core.management.base import BaseCommand
import random
from collections import defaultdict

from public_api.models import Dataset, Paper

class Command(BaseCommand):
    help = 'Generate similar dataset relationships based on common categories and papers'

    def handle(self, *args, **options):
        self.stdout.write("Starting similar datasets generation...")
        
        # Get all datasets
        datasets = Dataset.objects.all()
        total_datasets = datasets.count()
        
        if total_datasets == 0:
            self.stdout.write(self.style.ERROR("No datasets found in the database."))
            return
        
        self.stdout.write(f"Found {total_datasets} datasets.")
        
        # Clear existing similar_datasets relationships
        self.stdout.write("Clearing existing similar dataset relationships...")
        for dataset in datasets:
            dataset.similar_datasets.clear()
        
        # Group datasets by data_type/category
        self.stdout.write("Grouping datasets by category...")
        datasets_by_category = defaultdict(list)
        for dataset in datasets:
            category = dataset.data_type or "unknown"
            datasets_by_category[category].append(dataset)
        
        # Find datasets used by the same papers
        self.stdout.write("Finding datasets used by the same papers...")
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
        self.stdout.write("Setting similar datasets based on category...")
        for category, category_datasets in datasets_by_category.items():
            if len(category_datasets) > 1:
                for dataset in category_datasets:
                    # Get other datasets in the same category
                    similar_in_category = [d for d in category_datasets if d.id != dataset.id]
                    
                    # Add up to 5 similar datasets from the same category
                    for similar in random.sample(similar_in_category, min(5, len(similar_in_category))):
                        dataset.similar_datasets.add(similar)
        
        # Add similar datasets based on common papers
        self.stdout.write("Adding similar datasets based on common papers...")
        for dataset in datasets:
            common_paper_datasets = datasets_with_common_papers.get(dataset.id, set())
            if common_paper_datasets:
                # Get the actual dataset objects
                similar_datasets = Dataset.objects.filter(id__in=common_paper_datasets)
                
                # Add up to 3 similar datasets based on common papers
                for similar in similar_datasets[:3]:
                    dataset.similar_datasets.add(similar)
        
        # Ensure each dataset has at least some similar datasets
        self.stdout.write("Ensuring each dataset has similar datasets...")
        for dataset in datasets:
            if dataset.similar_datasets.count() == 0:
                # Find random datasets to add as similar
                potential_similar = Dataset.objects.exclude(id=dataset.id).order_by('?')[:3]
                for similar in potential_similar:
                    dataset.similar_datasets.add(similar)
        
        # Count total relationships created
        total_relationships = sum(dataset.similar_datasets.count() for dataset in datasets)
        self.stdout.write(
            self.style.SUCCESS(f"Process complete! Created {total_relationships} similar dataset relationships.")
        ) 