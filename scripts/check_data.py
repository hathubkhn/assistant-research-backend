import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auth_project.settings')
django.setup()

# Import models
from public_api.models import Journal, Conference

# Check journal data
print(f'Journals count: {Journal.objects.count()}')
print('Sample journals:')
for journal in Journal.objects.all()[:5]:
    print(f'- {journal.name} (IF: {journal.impact_factor}, Q: {journal.quartile}, Publisher: {journal.publisher})')

# Check conference data
print(f'\nConferences count: {Conference.objects.count()}')
print('Sample conferences:')
for conference in Conference.objects.all()[:5]:
    print(f'- {conference.name} (Abbr: {conference.abbreviation}, Rank: {conference.rank})') 