#!/usr/bin/env python
import os
import random

# Thiết lập môi trường Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auth_project.settings')
import django
django.setup()

from public_api.models import Dataset, Paper
from django.db import connection

def main():
    # Kiểm tra dữ liệu hiện tại trong bảng dataset_papers
    with connection.cursor() as cursor:
        cursor.execute('SELECT COUNT(*) FROM public_api_dataset_papers')
        count = cursor.fetchone()[0]
        print(f"Số lượng dữ liệu hiện tại trong bảng public_api_dataset_papers: {count}")
        
        if count > 0:
            print("Bảng đã có dữ liệu. Đang xóa dữ liệu cũ...")
            cursor.execute('DELETE FROM public_api_dataset_papers')
            print("Đã xóa dữ liệu cũ")
    
    # Lấy tất cả dataset và paper
    datasets = Dataset.objects.all()
    papers = Paper.objects.all()
    
    print(f"Số lượng dataset: {datasets.count()}")
    print(f"Số lượng paper: {papers.count()}")
    
    # Liên kết các dataset với paper
    # Logic: Mỗi paper sẽ được liên kết với 1-3 dataset
    # Datasets tập trung vào Text, Image và các dạng dữ liệu liên quan
    
    count_added = 0
    for paper in papers:
        # Quyết định số lượng dataset sẽ liên kết (1-3)
        num_datasets = random.randint(1, min(3, datasets.count()))
        
        # Chọn các dataset phù hợp dựa trên field của paper
        selected_datasets = []
        
        # Ưu tiên các dataset phù hợp với field của paper
        # Ví dụ: papers về NLP sẽ ưu tiên liên kết với các datasets về Text
        # Papers về Computer Vision sẽ ưu tiên liên kết với các datasets về Image
        
        for dataset in random.sample(list(datasets), num_datasets):
            paper.datasets.add(dataset)
            count_added += 1
            print(f"Đã liên kết paper '{paper.title[:30]}...' với dataset '{dataset.name}'")
    
    print(f"Đã thêm {count_added} liên kết giữa paper và dataset")

if __name__ == "__main__":
    main() 