import json
import uuid
from django.core.management.base import BaseCommand
from django.db import transaction
from public_api.models import Dataset

class Command(BaseCommand):
    help = 'Delete existing datasets and import from datasets_full.json'

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, default='data/datasets_full.json', 
                          help='Path to the datasets_full.json file')
        parser.add_argument('--keep-existing', action='store_true',
                          help='Keep existing datasets instead of deleting them')

    def handle(self, *args, **options):
        json_file = options['file']
        keep_existing = options.get('keep_existing', False)
        
        self.stdout.write(f"Loading datasets from {json_file}")
        
        try:
            with open(json_file, 'r', encoding='utf-8') as file:
                datasets = json.load(file)
                
            self.stdout.write(f"Found {len(datasets)} datasets in JSON file")
            
            with transaction.atomic():
                # Delete existing datasets unless keep_existing is True
                if not keep_existing:
                    dataset_count = Dataset.objects.count()
                    self.stdout.write(f"Deleting {dataset_count} existing datasets...")
                    Dataset.objects.all().delete()
                    self.stdout.write("All existing datasets deleted.")
                
                # Import new datasets
                imported_count = 0
                for dataset_data in datasets:
                    try:
                        self._import_dataset(dataset_data)
                        imported_count += 1
                        if imported_count % 100 == 0:
                            self.stdout.write(f"Imported {imported_count} datasets...")
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Error importing dataset '{dataset_data.get('name')}': {str(e)}"))
                
                self.stdout.write(self.style.SUCCESS(f"Successfully imported {imported_count} datasets"))
                
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"File not found: {json_file}"))
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR(f"Invalid JSON format in {json_file}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))
    
    def _import_dataset(self, data):
        """Import a single dataset from JSON data"""
        # Map JSON fields to model fields
        field_mapping = {
            'name': 'name',
            'description': 'description',
            'category': 'data_type',
            'link': 'link',
            'subtitle': 'subtitle',
            'paper link': 'paper_link',
            'thumbnailUrl': 'thumbnailUrl',
            'language': 'language',
            'abbreviation': 'abbreviation',
            'paperCount': 'paperCount',
            'downloadUrl': 'source_url',
        }
        
        dataset_kwargs = {
            'id': uuid.uuid4(),
        }
        
        # Map fields from JSON to model fields
        for json_field, model_field in field_mapping.items():
            if json_field in data:
                dataset_kwargs[model_field] = data[json_field]
        
        # Handle JSON array fields
        if 'benchmarks' in data:
            dataset_kwargs['benchmarks'] = data['benchmarks']
        
        if 'tasks' in data:
            dataset_kwargs['tasks'] = data['tasks']
        
        if 'dataloaders' in data:
            dataset_kwargs['dataloaders'] = data['dataloaders']
        
        if 'papers' in data:
            dataset_kwargs['dataset_papers'] = data['papers']
        
        # Create the dataset
        dataset = Dataset.objects.create(**dataset_kwargs)
        
        return dataset 