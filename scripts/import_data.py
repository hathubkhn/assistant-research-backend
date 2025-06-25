#!/usr/bin/env python
"""
Script to import data from JSON and CSV files into PostgreSQL database.
This script loads papers, datasets, journals, and conferences into the database.
"""
import os
import sys
import json
import csv
import random
import pandas as pd
from datetime import datetime
from tqdm import tqdm
from django.utils import timezone

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auth_project.settings')

import django
django.setup()

from django.db import transaction
from django.contrib.auth.models import User
from users.models import Paper, ResearchPaper, Dataset, DatasetReference, Publication

# Paths to data files
PAPERS_FILE = 'backend/data/papers_full.json'
DATASETS_FILE = 'backend/data/datasets_full.json'
CONFERENCE_FILE = 'backend/data/conference.xlsx'
JOURNALS_FILE = 'backend/data/scimagojr 2024.csv'

# Create a default admin user if it doesn't exist
def ensure_admin_user():
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@example.com', 'admin')
        print("Created admin user.")
    return User.objects.get(username='admin')

# Load conference data from Excel file
def load_conferences():
    try:
        df = pd.read_excel(CONFERENCE_FILE)
        conferences = {}
        for _, row in df.iterrows():
            # Assuming the Excel has columns for conference name, year, etc.
            # Adjust according to the actual structure
            conf_name = row.get('Name', '')
            if conf_name:
                conferences[conf_name.lower()] = {
                    'name': conf_name,
                    'year': row.get('Year', random.randint(2015, 2023)),
                    'field': row.get('Field', 'Computer Science')
                }
        print(f"Loaded {len(conferences)} conferences.")
        return conferences
    except Exception as e:
        print(f"Error loading conferences: {e}")
        # Return a default dictionary with some common conferences
        return {
            'cvpr': {'name': 'CVPR', 'year': 2023, 'field': 'Computer Vision'},
            'nips': {'name': 'NeurIPS', 'year': 2023, 'field': 'Machine Learning'},
            'icml': {'name': 'ICML', 'year': 2023, 'field': 'Machine Learning'},
            'iclr': {'name': 'ICLR', 'year': 2023, 'field': 'Deep Learning'},
            'acl': {'name': 'ACL', 'year': 2023, 'field': 'Natural Language Processing'},
            'emnlp': {'name': 'EMNLP', 'year': 2023, 'field': 'Natural Language Processing'},
            'sigir': {'name': 'SIGIR', 'year': 2023, 'field': 'Information Retrieval'},
            'kdd': {'name': 'KDD', 'year': 2023, 'field': 'Data Mining'},
            'www': {'name': 'WWW', 'year': 2023, 'field': 'Web Technologies'},
            'aaai': {'name': 'AAAI', 'year': 2023, 'field': 'Artificial Intelligence'}
        }

# Load journal data from CSV file
def load_journals():
    journals = {}
    try:
        with open(JOURNALS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter=';')
            next(reader)  # Skip header
            for row in reader:
                if len(row) >= 3:  # Ensure row has enough columns
                    journal_name = row[2].strip('"')
                    journals[journal_name.lower()] = {
                        'name': journal_name,
                        'issn': row[4] if len(row) > 4 else '',
                        'rank': row[0] if len(row) > 0 else '',
                        'sjr': row[5] if len(row) > 5 else '',
                        'h_index': row[7] if len(row) > 7 else ''
                    }
        print(f"Loaded {len(journals)} journals.")
        return journals
    except Exception as e:
        print(f"Error loading journals: {e}")
        # Return some default journals
        return {
            'nature': {'name': 'Nature', 'issn': '0028-0836', 'rank': '1', 'sjr': '17.875', 'h_index': '1145'},
            'science': {'name': 'Science', 'issn': '0036-8075', 'rank': '2', 'sjr': '16.192', 'h_index': '1120'},
            'cell': {'name': 'Cell', 'issn': '0092-8674', 'rank': '3', 'sjr': '22.612', 'h_index': '925'},
            'ieee transactions on pattern analysis and machine intelligence': {
                'name': 'IEEE Transactions on Pattern Analysis and Machine Intelligence',
                'issn': '0162-8828', 'rank': '100', 'sjr': '5.285', 'h_index': '354'
            },
            'neural information processing systems': {
                'name': 'Neural Information Processing Systems',
                'issn': '1049-5258', 'rank': '150', 'sjr': '4.218', 'h_index': '210'
            }
        }

# Generate a fake BibTeX citation
def generate_bibtex(paper):
    title = paper.get('title', 'Unknown Title')
    authors = paper.get('authors', [])
    conf = paper.get('conference', '')
    year = paper.get('year', 2023)
    
    author_str = ' and '.join(authors) if authors else 'Unknown Author'
    
    # Generate a key based on first author's last name and year
    first_author = authors[0].split()[-1] if authors else 'Unknown'
    key = f"{first_author.lower()}{year}"
    
    return f"""@inproceedings{{{key},
  title={{{title}}},
  author={{{author_str}}},
  booktitle={{{conf}}},
  year={{{year}}},
}}"""

# Import datasets
def import_datasets():
    try:
        with open(DATASETS_FILE, 'r', encoding='utf-8') as f:
            datasets_data = json.load(f)
        
        print(f"Importing {len(datasets_data)} datasets...")
        dataset_mapping = {}  # To store dataset name -> ID mapping
        
        with transaction.atomic():
            # Clear existing data
            Dataset.objects.all().delete()
            
            for idx, dataset in enumerate(tqdm(datasets_data)):
                name = dataset.get('name', f'Dataset {idx}')
                description = dataset.get('description', '')
                
                # Generate a unique ID
                dataset_id = f"dataset_{idx}"
                
                # Create dataset record
                ds = Dataset(
                    id=dataset_id,
                    name=name,
                    abbreviation=name.split()[0] if ' ' in name else name[:3].upper(),
                    description=description,
                    downloadUrl=dataset.get('link', ''),
                    paperCount=len(dataset.get('papers', [])),
                    language='English',  # Default
                    category=dataset.get('papers', [{}])[0].get('tasks', ['Other'])[0] if dataset.get('papers') else 'Other',
                    tasks=dataset.get('benchmarks', [{}])[0].get('task', 'Other') if dataset.get('benchmarks') else ['Other'],
                    thumbnailUrl='',
                    benchmarks=len(dataset.get('benchmarks', [])),
                    created_at=timezone.now(),
                    updated_at=timezone.now()
                )
                ds.save()
                
                # Store mapping from name to ID
                dataset_mapping[name.lower()] = dataset_id
                
        print(f"Imported {len(dataset_mapping)} datasets.")
        return dataset_mapping
    except Exception as e:
        print(f"Error importing datasets: {e}")
        return {}

# Import papers
def import_papers(dataset_mapping, conferences, journals, admin_user):
    try:
        with open(PAPERS_FILE, 'r', encoding='utf-8') as f:
            papers_data = json.load(f)
        
        print(f"Importing papers...")
        papers_count = 0
        dataset_refs_count = 0
        publication_count = 0
        
        with transaction.atomic():
            # Clear existing data
            ResearchPaper.objects.all().delete()
            DatasetReference.objects.all().delete()
            Paper.objects.all().delete()
            Publication.objects.all().delete()
            
            paper_items = list(papers_data.items())
            
            for i, (paper_url, paper) in enumerate(tqdm(paper_items[:1000])):  # Import first 1000 for demo
                title = paper.get('title', f'Untitled Paper {i}')
                authors = paper.get('authors', ['Unknown Author'])
                abstract = paper.get('abtract', '')  # Note: 'abtract' typo in the data
                
                # Handle conference information
                conference_name = paper.get('conference', '').lower()
                conf_info = conferences.get(conference_name, {})
                
                # Extract year or use from conference info
                try:
                    year = int(paper.get('year', conf_info.get('year', 2023)))
                except (ValueError, TypeError):
                    year = 2023
                
                # Generate a unique ID
                paper_id = f"paper_{i}"
                
                # Create ResearchPaper record
                rp = ResearchPaper(
                    id=paper_id,
                    title=title,
                    authors=authors,
                    conference=conf_info.get('name', paper.get('conference', '')),
                    year=year,
                    field=conf_info.get('field', 'Computer Science'),
                    keywords=paper.get('tasks', []),
                    abstract=abstract,
                    downloadUrl=paper.get('pdf_link', ''),
                    doi=f"10.1000/paper{i}",  # Fake DOI
                    method="",
                    results="",
                    conclusions="",
                    bibtex=generate_bibtex(paper),
                    sourceCode=paper.get('codes', [''])[0] if paper.get('codes') else '',
                    created_at=timezone.now(),
                    updated_at=timezone.now()
                )
                rp.save()
                papers_count += 1
                
                # Create Paper record (for user-facing model)
                user_paper = Paper(
                    user=admin_user,
                    title=title,
                    authors=authors,
                    conference=conf_info.get('name', paper.get('conference', '')),
                    year=year,
                    field=conf_info.get('field', 'Computer Science'),
                    keywords=paper.get('tasks', []),
                    abstract=abstract,
                    doi=f"10.1000/paper{i}",  # Fake DOI
                    bibtex=generate_bibtex(paper),
                    sourceCode=paper.get('codes', [''])[0] if paper.get('codes') else '',
                    is_interesting=random.choice([True, False]),
                    is_downloaded=True,
                    is_uploaded=False,
                    file=None,
                    file_name=f"{title[:30]}.pdf".replace(' ', '_'),
                    file_size=random.randint(500_000, 5_000_000)  # Random file size
                )
                user_paper.save()
                
                # Create dataset references
                datasets_info = paper.get('datasets', {})
                used_datasets = datasets_info.get('used', [])
                introduced_datasets = datasets_info.get('introduced', [])
                
                # Process all datasets related to this paper
                all_related_datasets = used_datasets + introduced_datasets
                for dataset_name in all_related_datasets:
                    dataset_id = dataset_mapping.get(dataset_name.lower() if isinstance(dataset_name, str) else str(dataset_name).lower())
                    if dataset_id and Dataset.objects.filter(id=dataset_id).exists():
                        dataset = Dataset.objects.get(id=dataset_id)
                        DatasetReference.objects.create(
                            paper=rp,
                            dataset=dataset
                        )
                        dataset_refs_count += 1
                
                # Create Publication record (if it has a journal)
                # Check if the conference name matches any journal name
                journal_match = None
                for journal_name, journal_info in journals.items():
                    if journal_name in conference_name or conference_name in journal_name:
                        journal_match = journal_info
                        break
                
                if journal_match:
                    Publication.objects.create(
                        user=admin_user,
                        title=title,
                        authors=', '.join(authors),
                        journal=journal_match['name'],
                        year=year,
                        url=paper_url,
                        created_at=timezone.now(),
                        updated_at=timezone.now()
                    )
                    publication_count += 1
        
        print(f"Imported {papers_count} papers, {dataset_refs_count} dataset references, and {publication_count} journal publications.")
    except Exception as e:
        print(f"Error importing papers: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("Starting data import process...")
    admin_user = ensure_admin_user()
    
    print("Loading conferences...")
    conferences = load_conferences()
    
    print("Loading journals...")
    journals = load_journals()
    
    print("Importing datasets...")
    dataset_mapping = import_datasets()
    
    print("Importing papers...")
    import_papers(dataset_mapping, conferences, journals, admin_user)
    
    print("Data import completed!")

if __name__ == "__main__":
    main() 