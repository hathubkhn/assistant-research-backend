import os
import json
import logging
from django.core.management.base import BaseCommand
from public_api.models import Dataset, DatasetSimilarDataset
from django.db import transaction

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Import similar datasets from datasets_full.json into the database'

    def add_arguments(self, parser):
        parser.add_argument('--json-file', type=str, default='backend/data/datasets_full.json',
                           help='Path to the datasets JSON file')

    def handle(self, *args, **options):
        file_path = options['json_file']
        
        if not os.path.exists(file_path):
            self.stderr.write(self.style.ERROR(f'File {file_path} does not exist'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'Importing similar datasets from {file_path}'))
        
        # Read JSON file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                datasets_data = json.load(f)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error reading JSON file: {str(e)}'))
            return
            
        # Create dataset name to ID mapping
        dataset_map = {dataset.name: dataset.id for dataset in Dataset.objects.all()}
        
        # Clear existing similar datasets relationships
        DatasetSimilarDataset.objects.all().delete()
        
        # Counter for similar datasets created
        relations_created = 0
        datasets_processed = 0
        
        # Process each dataset
        with transaction.atomic():
            for dataset_data in datasets_data:
                try:
                    dataset_name = dataset_data.get('name')
                    
                    # Skip if dataset name is not in the database
                    if dataset_name not in dataset_map:
                        continue
                    
                    from_dataset_id = dataset_map[dataset_name]
                    from_dataset = Dataset.objects.get(id=from_dataset_id)
                    datasets_processed += 1
                    
                    # Get similar datasets array if it exists
                    similar_datasets = dataset_data.get('similar datasets', [])
                    
                    for similar in similar_datasets:
                        similar_name = similar.get('name')
                        
                        # Skip if similar dataset name is not in the database
                        if similar_name not in dataset_map:
                            continue
                            
                        to_dataset_id = dataset_map[similar_name]
                        
                        # Don't create self-relationships
                        if from_dataset_id == to_dataset_id:
                            continue
                            
                        # Create the relationship
                        DatasetSimilarDataset.objects.get_or_create(
                            from_dataset_id=from_dataset_id,
                            to_dataset_id=to_dataset_id
                        )
                        relations_created += 1
                        
                except Exception as e:
                    logger.error(f"Error processing dataset: {str(e)}")
                    continue
                    
        self.stdout.write(self.style.SUCCESS(
            f'Processed {datasets_processed} datasets and created {relations_created} similar dataset relationships')
        ) 