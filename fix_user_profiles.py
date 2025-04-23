import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auth_project.settings')
django.setup()

from django.contrib.auth.models import User
from users.models import UserProfile
from public_api.models import Profile

def sync_user_profiles():
    # Get all users
    users = User.objects.all()
    print(f"Found {users.count()} users")
    
    # Counters for reporting
    created_user_profiles = 0
    created_public_profiles = 0
    
    for user in users:
        # Check and create UserProfile if it doesn't exist
        try:
            user_profile = UserProfile.objects.get(user=user)
            print(f"User {user.username} already has a UserProfile")
        except UserProfile.DoesNotExist:
            user_profile = UserProfile.objects.create(
                user=user,
                full_name=f"{user.first_name} {user.last_name}".strip() or user.username,
                is_profile_completed=False
            )
            created_user_profiles += 1
            print(f"Created UserProfile for user {user.username}")
        
        # Check and create Profile if it doesn't exist
        try:
            public_profile = Profile.objects.get(user=user)
            print(f"User {user.username} already has a PublicProfile")
        except Profile.DoesNotExist:
            public_profile = Profile.objects.create(
                user=user,
                name=user_profile.full_name or f"{user.first_name} {user.last_name}".strip() or user.username,
                institution=user_profile.faculty_institute or "",
                role=user_profile.position or "",
                bio=user_profile.bio or "",
                research_interests=user_profile.research_interests or ""
            )
            created_public_profiles += 1
            print(f"Created PublicProfile for user {user.username}")
        
        # Sync data from UserProfile to Profile if they both exist
        if hasattr(user, 'profile') and hasattr(user, 'public_profile'):
            has_changes = False
            
            if user.profile.full_name and user.profile.full_name != user.public_profile.name:
                user.public_profile.name = user.profile.full_name
                has_changes = True
                
            if user.profile.faculty_institute and user.profile.faculty_institute != user.public_profile.institution:
                user.public_profile.institution = user.profile.faculty_institute
                has_changes = True
                
            if user.profile.position and user.profile.position != user.public_profile.role:
                user.public_profile.role = user.profile.position
                has_changes = True
                
            if user.profile.bio and user.profile.bio != user.public_profile.bio:
                user.public_profile.bio = user.profile.bio
                has_changes = True
                
            if user.profile.research_interests and user.profile.research_interests != user.public_profile.research_interests:
                user.public_profile.research_interests = user.profile.research_interests
                has_changes = True
                
            if has_changes:
                user.public_profile.save()
                print(f"Updated PublicProfile for user {user.username} with data from UserProfile")
    
    print(f"\nSync completed:")
    print(f"- Created {created_user_profiles} new UserProfile entries")
    print(f"- Created {created_public_profiles} new PublicProfile entries")
    print(f"- Total users: {User.objects.count()}")
    print(f"- Total UserProfiles: {UserProfile.objects.count()}")
    print(f"- Total PublicProfiles: {Profile.objects.count()}")

if __name__ == "__main__":
    sync_user_profiles() 