#!/usr/bin/env python
"""
Script to check the current working directory and file existence
"""
import os
import sys

print(f"Current working directory: {os.getcwd()}")

# List of files to check
files_to_check = [
    'backend/data/papers_full.json',
    'backend/data/datasets_full.json',
    'backend/data/conference.xlsx',
    'backend/data/scimagojr 2024.csv'
]

# Check if files exist
for file_path in files_to_check:
    print(f"Checking {file_path}: {'Exists' if os.path.exists(file_path) else 'Not Found'}")

# Check if files exist from project root
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
print(f"Project root: {project_root}")
for file_path in files_to_check:
    abs_path = os.path.join(project_root, file_path)
    print(f"Checking {abs_path}: {'Exists' if os.path.exists(abs_path) else 'Not Found'}") 