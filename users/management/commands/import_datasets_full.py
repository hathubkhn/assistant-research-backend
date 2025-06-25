import json
import os
import uuid
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from users.models import Dataset, ResearchPaper, DatasetReference
import random

class Command(BaseCommand):
    help = 'Import datasets from datasets_full.json file into the database with all fields'

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete-existing',
            action='store_true',
            help='Delete existing dataset records before importing',
        )

    def handle(self, *args, **options):
        # Get path to the datasets file
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        data_file = os.path.join(base_dir, 'data', 'datasets_full.json')
        
        self.stdout.write(f"Importing datasets from {data_file}")
        
        try:
            # Open and read the JSON file
            with open(data_file, 'r', encoding='utf-8') as f:
                datasets_data = json.load(f)
            
            self.stdout.write(f"Found {len(datasets_data)} datasets in file")
            
            # Start database transaction
            with transaction.atomic():
                # Delete existing datasets if requested
                if options['delete_existing']:
                    self.stdout.write("Deleting existing datasets...")
                    Dataset.objects.all().delete()
                    DatasetReference.objects.all().delete()
                
                # Keep track of created datasets
                created_count = 0
                skipped_count = 0
                
                # Get all existing papers
                papers = ResearchPaper.objects.all()
                paper_map = {paper.title.lower(): paper for paper in papers}
                
                # Process each dataset
                for idx, dataset in enumerate(datasets_data):
                    name = dataset.get('name')
                    
                    # Skip if no name
                    if not name:
                        skipped_count += 1
                        continue
                    
                    # Generate a unique ID
                    dataset_id = f"dataset_{idx}"
                    
                    # Get paper count from the papers array
                    paper_count = len(dataset.get('papers', []))
                    
                    # Get abbreviation from name (first word or first 3 characters)
                    abbreviation = name.split()[0] if ' ' in name else name[:3].upper()
                    
                    # Extract tasks from papers or benchmarks or set default
                    tasks = []
                    if 'tasks' in dataset and dataset['tasks']:
                        tasks = dataset['tasks']
                    elif dataset.get('benchmarks') and len(dataset['benchmarks']) > 0:
                        for benchmark in dataset['benchmarks']:
                            if 'task' in benchmark and benchmark['task'] not in tasks:
                                tasks.append(benchmark['task'])
                    elif dataset.get('papers') and len(dataset['papers']) > 0:
                        for paper in dataset['papers']:
                            if 'tasks' in paper and isinstance(paper['tasks'], list):
                                for task in paper['tasks']:
                                    if task not in tasks:
                                        tasks.append(task)
                                        
                    # Set default category from tasks or default
                    category = 'Other'
                    if tasks:
                        category = tasks[0]
                    
                    # Create dataset object with all available fields
                    ds = Dataset(
                        id=dataset_id,
                        name=name,
                        abbreviation=abbreviation,
                        description=dataset.get('description', ''),
                        downloadUrl=dataset.get('link', ''),
                        link=dataset.get('link', ''),
                        paper_link=dataset.get('paper link', ''),
                        subtitle=dataset.get('subtitle', ''),
                        paperCount=paper_count,
                        language='English',  # Default
                        category=category,
                        tasks=tasks,
                        thumbnailUrl='',
                        benchmarks=dataset.get('benchmarks', []),
                        dataloaders=dataset.get('dataloaders', []),
                        similar_datasets=dataset.get('similar datasets', []),
                        papers=dataset.get('papers', []),
                        created_at=timezone.now(),
                        updated_at=timezone.now()
                    )
                    ds.save()
                    created_count += 1
                    
                    # Create dataset references to papers
                    dataset_papers = dataset.get('papers', [])
                    linked_papers = 0
                    
                    for paper_data in dataset_papers:
                        paper_title = paper_data.get('title', '').lower()
                        if paper_title in paper_map:
                            paper = paper_map[paper_title]
                            # Create reference if it doesn't exist
                            DatasetReference.objects.get_or_create(
                                paper=paper,
                                dataset=ds
                            )
                            linked_papers += 1
                    
                    # Log progress every 100 datasets
                    if created_count % 100 == 0:
                        self.stdout.write(f"Progress: {created_count} datasets imported")
                
                self.stdout.write(self.style.SUCCESS(
                    f"Successfully imported {created_count} datasets ({skipped_count} skipped)"
                ))
                
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"File not found: {data_file}"))
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR(f"Invalid JSON format in {data_file}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error importing datasets: {str(e)}")) 