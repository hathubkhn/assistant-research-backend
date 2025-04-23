from django.contrib.auth.models import User
from users.models import UserProfile
from public_api.models import Profile, Publication

def run():
    users = User.objects.all()[:5]
    print(f"Total users: {User.objects.count()}")
    print(f"Total user profiles: {UserProfile.objects.count()}")
    print(f"Total public profiles: {Profile.objects.count()}")
    print(f"Total publications: {Publication.objects.count()}")
    
    print("\nChecking first 5 users:")
    for user in users:
        print(f"User: {user.username}")
        try:
            profile = UserProfile.objects.get(user=user)
            print(f"  - Has UserProfile: Yes (ID: {profile.id})")
        except UserProfile.DoesNotExist:
            print(f"  - Has UserProfile: No")
            
        try:
            public_profile = Profile.objects.get(user=user)
            print(f"  - Has PublicProfile: Yes (ID: {public_profile.id})")
        except Profile.DoesNotExist:
            print(f"  - Has PublicProfile: No")
            
        publications = Publication.objects.filter(user=user)
        print(f"  - Publications: {publications.count()}")

if __name__ == "__main__":
    import django
    django.setup()
    run() 