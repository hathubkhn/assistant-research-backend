import os
import sys
import django
import random
from datetime import datetime

# Get the project base directory and add it to the Python path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auth_project.settings')
django.setup()

from users.models import Paper, PaperCitation

def populate_user_citations():
    """
    Populate citation data for user-uploaded papers
    """
    papers = Paper.objects.all()
    print(f"Found {papers.count()} papers in users app")
    
    current_year = datetime.now().year
    
    for paper in papers:
        # Delete existing citations for this paper
        paper.citations.all().delete()
        
        # Calculate starting year - we'll start from the publication year
        start_year = paper.year if paper.year else current_year - 5  # Use a default if year is None
        
        # Don't generate citations for papers from the future
        if start_year > current_year:
            continue
            
        # Generate citation data for each year from publication until current year
        for year in range(start_year, current_year + 1):
            # Citations tend to increase for the first few years then plateau or decrease
            years_since_publication = year - start_year
            
            if years_since_publication == 0:
                # Few citations in the publication year
                count = random.randint(0, 3)
            elif years_since_publication < 3:
                # Citations increase in first few years
                count = random.randint(5, 20) * years_since_publication
            elif years_since_publication < 6:
                # Citations peak
                count = random.randint(15, 40)
            else:
                # Citations start to decrease or plateau for older papers
                count = random.randint(5, 30)
                
            # Create citation record
            PaperCitation.objects.create(
                paper=paper,
                year=year,
                count=count
            )
        
        print(f"Generated citations for '{paper.title}'")

if __name__ == "__main__":
    populate_user_citations()
    print("Done!") 