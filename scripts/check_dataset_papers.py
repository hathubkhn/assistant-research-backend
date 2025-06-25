#!/usr/bin/env python
import os

# Thiết lập môi trường Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auth_project.settings')
import django
django.setup()

from public_api.models import Dataset, Paper
from django.db import connection

def main():
    # Kiểm tra dữ liệu trong bảng dataset_papers
    with connection.cursor() as cursor:
        cursor.execute('SELECT COUNT(*) FROM public_api_dataset_papers')
        count = cursor.fetchone()[0]
        print(f"Số lượng dữ liệu trong bảng public_api_dataset_papers: {count}")
        
        cursor.execute('''
            SELECT p.title, d.name 
            FROM public_api_dataset_papers dp
            JOIN public_api_paper p ON dp.paper_id = p.id
            JOIN public_api_dataset d ON dp.dataset_id = d.id
        ''')
        
        print("\nMối quan hệ giữa paper và dataset:")
        for row in cursor.fetchall():
            paper_title, dataset_name = row
            print(f"Paper: {paper_title[:50]}... | Dataset: {dataset_name}")
            
    # Kiểm tra xem mỗi paper có bao nhiêu dataset
    print("\nSố lượng dataset cho mỗi paper:")
    for paper in Paper.objects.all():
        dataset_count = paper.datasets.count()
        print(f"Paper: {paper.title[:50]}... | Số dataset: {dataset_count}")
    
    # Kiểm tra xem mỗi dataset có bao nhiêu paper
    print("\nSố lượng paper cho mỗi dataset:")
    for dataset in Dataset.objects.all():
        paper_count = dataset.papers.count()
        print(f"Dataset: {dataset.name} | Số paper: {paper_count}")

if __name__ == "__main__":
    main() 