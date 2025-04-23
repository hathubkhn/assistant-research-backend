from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from users.models import UserProfile
from public_api.models import Profile

class Command(BaseCommand):
    help = 'Synchronize user profiles between UserProfile and Profile models'

    def handle(self, *args, **kwargs):
        # Get all users
        users = User.objects.all()
        self.stdout.write(f"Found {users.count()} users")
        
        # Counters for reporting
        created_user_profiles = 0
        created_public_profiles = 0
        updated_profiles = 0
        
        for user in users:
            # Check and create UserProfile if it doesn't exist
            try:
                user_profile = UserProfile.objects.get(user=user)
                self.stdout.write(self.style.SUCCESS(f"User {user.username} already has a UserProfile"))
            except UserProfile.DoesNotExist:
                user_profile = UserProfile.objects.create(
                    user=user,
                    full_name=f"{user.first_name} {user.last_name}".strip() or user.username,
                    is_profile_completed=False
                )
                created_user_profiles += 1
                self.stdout.write(self.style.SUCCESS(f"Created UserProfile for user {user.username}"))
            
            # Check and create Profile if it doesn't exist
            try:
                public_profile = Profile.objects.get(user=user)
                self.stdout.write(self.style.SUCCESS(f"User {user.username} already has a PublicProfile"))
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
                self.stdout.write(self.style.SUCCESS(f"Created PublicProfile for user {user.username}"))
            
            # Sync data between UserProfile and Profile
            if hasattr(user, 'profile') and hasattr(user, 'public_profile'):
                has_changes = False
                
                # From UserProfile to PublicProfile
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
                    updated_profiles += 1
                    self.stdout.write(self.style.SUCCESS(f"Updated PublicProfile for user {user.username} with data from UserProfile"))
        
        self.stdout.write(self.style.SUCCESS(f"\nSync completed:"))
        self.stdout.write(f"- Created {created_user_profiles} new UserProfile entries")
        self.stdout.write(f"- Created {created_public_profiles} new PublicProfile entries")
        self.stdout.write(f"- Updated {updated_profiles} existing profiles")
        self.stdout.write(f"- Total users: {User.objects.count()}")
        self.stdout.write(f"- Total UserProfiles: {UserProfile.objects.count()}")
        self.stdout.write(f"- Total PublicProfiles: {Profile.objects.count()}") 