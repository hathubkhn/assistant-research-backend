import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auth_project.settings')
os.environ['USE_POSTGRES'] = 'True'
django.setup()

# Import models after Django setup
from django.contrib.auth.models import User
from users.models import Publication

try:
    # Get or create a test user
    user, created = User.objects.get_or_create(
        username='testuser', 
        email='test@example.com'
    )
    if created:
        user.set_password('testpassword')
        user.save()
        print(f"Created test user: {user.username}")
    else:
        print(f"Using existing user: {user.username}")
    
    # Create a test publication
    publication = Publication.objects.create(
        user=user,
        title="Test Publication",
        authors="Test Author 1, Test Author 2",
        journal="Test Journal",
        year=2023,
        url="https://example.com/test"
    )
    print(f"Created publication: {publication.title}")
    
    # Verify by retrieving it
    retrieved = Publication.objects.get(id=publication.id)
    print(f"Retrieved publication: {retrieved.title}")
    
    # Clean up
    publication.delete()
    print("Test publication deleted")
    
    print("SUCCESS: Publication model test passed!")
    
except Exception as e:
    print(f"ERROR: {e}") 