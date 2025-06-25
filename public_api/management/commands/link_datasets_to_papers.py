import json
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from public_api.models import Dataset, Paper
import time

class Command(BaseCommand):
    help = 'Link datasets to papers based on dataset_papers JSON field'

    def add_arguments(self, parser):
        parser.add_argument('--batch-size', type=int, default=100, 
                          help='Number of datasets to process in each batch')
        parser.add_argument('--limit', type=int, default=None,
                          help='Limit the number of datasets to process (for testing)')

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        limit = options['limit']
        total_datasets = Dataset.objects.count()
        
        self.stdout.write(f"Found {total_datasets} datasets to process")
        
        # Get all datasets with dataset_papers field
        datasets_query = Dataset.objects.exclude(dataset_papers__isnull=True).exclude(dataset_papers=[])
        
        if limit:
            datasets_query = datasets_query[:limit]
            
        total_datasets_with_papers = datasets_query.count()
        
        self.stdout.write(f"Processing {total_datasets_with_papers} datasets with paper data")
        
        processed = 0
        created_links = 0
        start_time = time.time()
        
        # Pre-fetch existing papers and create a title lookup for faster matching
        self.stdout.write("Building paper title lookup table...")
        all_papers = list(Paper.objects.all())
        paper_title_lookup = {}
        for paper in all_papers:
            # Use lowercase title as key for case-insensitive lookup
            lower_title = paper.title.lower()
            if lower_title not in paper_title_lookup:
                paper_title_lookup[lower_title] = []
            paper_title_lookup[lower_title].append(paper)
            
        self.stdout.write(f"Built lookup table with {len(paper_title_lookup)} unique paper titles")
        
        # Process datasets in batches
        for i in range(0, total_datasets_with_papers, batch_size):
            batch_end = min(i + batch_size, total_datasets_with_papers)
            batch = list(datasets_query[i:batch_end])
            
            self.stdout.write(f"Processing batch {i//batch_size + 1}, datasets {i+1}-{batch_end}")
            
            with transaction.atomic():
                for dataset in batch:
                    try:
                        dataset_papers_data = dataset.dataset_papers or []
                        if not dataset_papers_data:
                            continue
                        
                        # Extract paper titles from the dataset_papers
                        paper_titles = [
                            paper_data.get('title') 
                            for paper_data in dataset_papers_data 
                            if paper_data.get('title')
                        ]
                        
                        if not paper_titles:
                            continue
                        
                        # Match papers by title using our lookup table
                        matched_papers = []
                        for title in paper_titles:
                            lower_title = title.lower()
                            if lower_title in paper_title_lookup:
                                matched_papers.extend(paper_title_lookup[lower_title])
                                
                        # Add papers to dataset in bulk
                        if matched_papers:
                            # Get IDs of papers already linked to this dataset
                            existing_paper_ids = set(dataset.papers.values_list('id', flat=True))
                            
                            # Filter out papers that are already linked
                            new_papers = [p for p in matched_papers if p.id not in existing_paper_ids]
                            
                            # Add the new papers to the dataset
                            dataset.papers.add(*new_papers)
                            created_links += len(new_papers)
                        
                        processed += 1
                    
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Error processing dataset {dataset.name}: {str(e)}"))
                
            # Report progress after each batch
            elapsed = time.time() - start_time
            papers_per_second = created_links / elapsed if elapsed > 0 else 0
            
            self.stdout.write(
                f"Processed {processed}/{total_datasets_with_papers} datasets, "
                f"created {created_links} links "
                f"({papers_per_second:.1f} links/sec)"
            )
            
        # Final report
        elapsed = time.time() - start_time
        papers_per_second = created_links / elapsed if elapsed > 0 else 0
        
        self.stdout.write(self.style.SUCCESS(
            f"Completed in {elapsed:.1f} seconds\n"
            f"Successfully processed {processed} datasets and created {created_links} "
            f"dataset-paper relationships ({papers_per_second:.1f} links/sec)"
        )) 