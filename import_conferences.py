#!/usr/bin/env python
import os
import django
import pandas as pd
import uuid

# Thiết lập môi trường Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auth_project.settings')
django.setup()

# Import model Conference
from public_api.models import Conference

def import_conferences():
    print("Bắt đầu import các hội nghị...")
    
    # Xóa tất cả dữ liệu hiện tại trong bảng Conference
    print("Xóa dữ liệu cũ từ bảng Conference...")
    Conference.objects.all().delete()
    
    # Đọc file Excel
    print("Đọc dữ liệu từ file Excel...")
    data = pd.read_excel('backend/data/conference.xlsx')
    
    # Import các hàng dữ liệu
    conferences = []
    for _, row in data.iterrows():
        conference = Conference(
            id=uuid.uuid4(),
            name=row['Title'],
            abbreviation=row['Acronym'] if pd.notna(row['Acronym']) else '',
            rank=row['Rank'] if pd.notna(row['Rank']) else '',
            # location không có trong dữ liệu Excel, để trống
            location='',
            url=''
        )
        conferences.append(conference)
    
    # Bulk create để tăng hiệu suất
    print(f"Import {len(conferences)} hội nghị...")
    Conference.objects.bulk_create(conferences)
    print("Import hoàn tất!")

if __name__ == "__main__":
    import_conferences() 